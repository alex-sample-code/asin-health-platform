"""
数据上传脚本 — 评分 -> DynamoDB, 原始指标/基准/知识库 -> S3。

DynamoDB 表: asin-health-scores (PK: seller_id#marketplace_id, SK: asin#date)
S3 桶: asin-health-platform-data-{account_id}
Region: us-east-1

用法:
    uv run python -m src.data.upload_data            # 执行上传
    uv run python -m src.data.upload_data --dry-run   # 只打印计划，不执行
"""

from __future__ import annotations

import argparse
import json
from decimal import Decimal
from pathlib import Path
from typing import Any

import boto3
from botocore.exceptions import ClientError

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
RAW_DIR = DATA_DIR / "raw"
SCORES_DIR = DATA_DIR / "scores"
BENCHMARK_DIR = DATA_DIR / "benchmarks"
KNOWLEDGE_DIR = DATA_DIR / "knowledge_docs"

REGION = "us-east-1"
DYNAMODB_TABLE = "asin-health-scores"


def _get_account_id() -> str:
    """获取当前 AWS 账号 ID。"""
    sts = boto3.client("sts", region_name=REGION)
    return sts.get_caller_identity()["Account"]


def _get_s3_bucket_name() -> str:
    """生成 S3 桶名（包含账号 ID 确保唯一）。"""
    account_id = _get_account_id()
    return f"asin-health-platform-data-{account_id}"


# ── DynamoDB ──────────────────────────────────────────────────────────────


def _create_dynamodb_table(dynamodb: Any) -> None:
    """创建 DynamoDB 表（如不存在）。"""
    try:
        dynamodb.describe_table(TableName=DYNAMODB_TABLE)
        print(f"  DynamoDB 表 '{DYNAMODB_TABLE}' 已存在")
        return
    except ClientError as e:
        if e.response["Error"]["Code"] != "ResourceNotFoundException":
            raise

    print(f"  创建 DynamoDB 表 '{DYNAMODB_TABLE}'...")
    dynamodb.create_table(
        TableName=DYNAMODB_TABLE,
        KeySchema=[
            {"AttributeName": "pk", "KeyType": "HASH"},
            {"AttributeName": "sk", "KeyType": "RANGE"},
        ],
        AttributeDefinitions=[
            {"AttributeName": "pk", "AttributeType": "S"},
            {"AttributeName": "sk", "AttributeType": "S"},
        ],
        BillingMode="PAY_PER_REQUEST",
    )
    waiter = dynamodb.get_waiter("table_exists")
    waiter.wait(TableName=DYNAMODB_TABLE)
    print(f"  DynamoDB 表 '{DYNAMODB_TABLE}' 创建完成")


def _float_to_decimal(obj: Any) -> Any:
    """递归将 float 转为 Decimal（DynamoDB 要求）。"""
    if isinstance(obj, float):
        return Decimal(str(obj))
    elif isinstance(obj, dict):
        return {k: _float_to_decimal(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_float_to_decimal(i) for i in obj]
    return obj


def upload_scores_to_dynamodb(*, dry_run: bool = False) -> None:
    """上传评分数据到 DynamoDB。"""
    scores_path = SCORES_DIR / "all_scores.json"
    with open(scores_path, "r", encoding="utf-8") as f:
        all_scores: list[dict[str, Any]] = json.load(f)

    print(f"  评分文件: {scores_path} ({len(all_scores)} 条)")
    print(f"  目标表: {DYNAMODB_TABLE}")

    if dry_run:
        print(f"  [DRY RUN] 跳过 DynamoDB 上传")
        return

    dynamodb = boto3.client("dynamodb", region_name=REGION)
    _create_dynamodb_table(dynamodb)

    table = boto3.resource("dynamodb", region_name=REGION).Table(DYNAMODB_TABLE)
    print(f"  上传 {len(all_scores)} 条评分到 DynamoDB...")
    with table.batch_writer() as batch:
        for score in all_scores:
            item = _float_to_decimal(score)
            item["pk"] = f"{score['seller_id']}#{score['marketplace_id']}"
            item["sk"] = f"{score['asin']}#{score['date']}"
            batch.put_item(Item=item)

    print(f"  DynamoDB 上传完成")


# ── S3 ────────────────────────────────────────────────────────────────────


def _create_s3_bucket(s3: Any, bucket: str) -> None:
    """创建 S3 桶（如不存在）。"""
    try:
        s3.head_bucket(Bucket=bucket)
        print(f"  S3 桶 '{bucket}' 已存在")
        return
    except ClientError as e:
        error_code = int(e.response["Error"]["Code"])
        if error_code != 404:
            raise

    print(f"  创建 S3 桶 '{bucket}'...")
    if REGION == "us-east-1":
        s3.create_bucket(Bucket=bucket)
    else:
        s3.create_bucket(
            Bucket=bucket,
            CreateBucketConfiguration={"LocationConstraint": REGION},
        )
    print(f"  S3 桶 '{bucket}' 创建完成")


def upload_raw_to_s3(bucket: str, *, dry_run: bool = False) -> None:
    """上传原始指标数据到 S3。"""
    profiles_path = RAW_DIR / "asin_profiles.json"
    daily_files = list(RAW_DIR.glob("*_daily.json"))
    summary_path = RAW_DIR / "all_asins_daily.json"

    print(f"  ASIN 资料: {profiles_path.name}")
    print(f"  每日指标文件: {len(daily_files)} 个")
    print(f"  汇总文件: {'存在' if summary_path.exists() else '不存在'}")
    print(f"  目标桶: s3://{bucket}/raw/")

    if dry_run:
        print(f"  [DRY RUN] 跳过 S3 上传")
        return

    s3 = boto3.client("s3", region_name=REGION)
    _create_s3_bucket(s3, bucket)

    s3.upload_file(str(profiles_path), bucket, "raw/asin_profiles.json")
    print(f"  上传 asin_profiles.json")

    print(f"  上传 {len(daily_files)} 个每日指标文件...")
    for fp in daily_files:
        s3.upload_file(str(fp), bucket, f"raw/{fp.name}")

    if summary_path.exists():
        s3.upload_file(str(summary_path), bucket, "raw/all_asins_daily.json")
        print(f"  上传汇总数据")

    print(f"  原始指标上传完成")


def upload_benchmarks_to_s3(bucket: str, *, dry_run: bool = False) -> None:
    """上传基准数据到 S3。"""
    benchmark_files = list(BENCHMARK_DIR.glob("*.json"))
    print(f"  基准文件: {len(benchmark_files)} 个")
    print(f"  目标桶: s3://{bucket}/benchmarks/")

    if dry_run:
        print(f"  [DRY RUN] 跳过 S3 上传")
        return

    s3 = boto3.client("s3", region_name=REGION)
    for fp in benchmark_files:
        s3.upload_file(str(fp), bucket, f"benchmarks/{fp.name}")
        print(f"  上传 {fp.name}")

    print(f"  基准数据上传完成")


def upload_knowledge_to_s3(bucket: str, *, dry_run: bool = False) -> None:
    """上传知识库文档到 S3。"""
    if not KNOWLEDGE_DIR.exists():
        print(f"  知识库目录不存在: {KNOWLEDGE_DIR}")
        return

    md_files = list(KNOWLEDGE_DIR.glob("*.md"))
    print(f"  知识库文档: {len(md_files)} 个")
    print(f"  目标桶: s3://{bucket}/knowledge_docs/")

    if dry_run:
        print(f"  [DRY RUN] 跳过 S3 上传")
        return

    s3 = boto3.client("s3", region_name=REGION)
    for fp in md_files:
        s3.upload_file(str(fp), bucket, f"knowledge_docs/{fp.name}")
        print(f"    {fp.name}")

    print(f"  知识库文档上传完成")


# ── 主流程 ────────────────────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(description="ASIN 健康度数据上传到 AWS")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="只打印上传计划，不实际执行",
    )
    args = parser.parse_args()
    dry_run: bool = args.dry_run

    print("=" * 50)
    print("ASIN 健康度数据上传")
    if dry_run:
        print("  *** DRY RUN 模式 — 不执行实际操作 ***")
    print("=" * 50)

    # 获取 S3 桶名
    if dry_run:
        bucket = "asin-health-platform-data-{account_id}"
        print(f"\n  S3 桶名: {bucket} (dry-run 模式下不解析实际账号)")
    else:
        bucket = _get_s3_bucket_name()
        print(f"\n  S3 桶名: {bucket}")

    print(f"\n[1/4] 上传评分到 DynamoDB...")
    upload_scores_to_dynamodb(dry_run=dry_run)

    print(f"\n[2/4] 上传原始指标到 S3...")
    upload_raw_to_s3(bucket, dry_run=dry_run)

    print(f"\n[3/4] 上传基准数据到 S3...")
    upload_benchmarks_to_s3(bucket, dry_run=dry_run)

    print(f"\n[4/4] 上传知识库文档到 S3...")
    upload_knowledge_to_s3(bucket, dry_run=dry_run)

    print("\n" + "=" * 50)
    if dry_run:
        print("DRY RUN 完成 — 以上为上传计划，未执行任何操作。")
        print("去掉 --dry-run 参数执行实际上传。")
    else:
        print("全部上传完成！")
        print(f"  DynamoDB 表: {DYNAMODB_TABLE}")
        print(f"  S3 桶: {bucket}")
    print("=" * 50)


if __name__ == "__main__":
    main()
