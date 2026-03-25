"""
数据上传脚本 — 评分 → DynamoDB, 原始指标/基准 → S3。

DynamoDB 表: asin_health_scores (PK: seller_id#marketplace_id, SK: asin#date)
S3 桶: asin-health-data-lake-959545103699
Region: us-east-1
"""

from __future__ import annotations

import json
import time
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
DYNAMODB_TABLE = "asin_health_scores"
S3_BUCKET = "asin-health-data-lake-959545103699"


# ── DynamoDB ──────────────────────────────────────────────────────────────

def _create_dynamodb_table(dynamodb: Any) -> None:
    """创建 DynamoDB 表（如不存在）"""
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
            {"AttributeName": "pk", "KeyType": "HASH"},   # seller_id#marketplace_id
            {"AttributeName": "sk", "KeyType": "RANGE"},   # asin#date
        ],
        AttributeDefinitions=[
            {"AttributeName": "pk", "AttributeType": "S"},
            {"AttributeName": "sk", "AttributeType": "S"},
        ],
        BillingMode="PAY_PER_REQUEST",
    )

    # 等待表创建完成
    waiter = dynamodb.get_waiter("table_exists")
    waiter.wait(TableName=DYNAMODB_TABLE)
    print(f"  DynamoDB 表 '{DYNAMODB_TABLE}' 创建完成")


def _float_to_decimal(obj: Any) -> Any:
    """递归将 float 转为 Decimal（DynamoDB 要求）"""
    if isinstance(obj, float):
        return Decimal(str(obj))
    elif isinstance(obj, dict):
        return {k: _float_to_decimal(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_float_to_decimal(i) for i in obj]
    return obj


def upload_scores_to_dynamodb() -> None:
    """上传评分数据到 DynamoDB"""
    dynamodb = boto3.client("dynamodb", region_name=REGION)
    _create_dynamodb_table(dynamodb)

    table = boto3.resource("dynamodb", region_name=REGION).Table(DYNAMODB_TABLE)

    scores_path = SCORES_DIR / "all_scores.json"
    with open(scores_path, "r", encoding="utf-8") as f:
        all_scores: list[dict[str, Any]] = json.load(f)

    print(f"  上传 {len(all_scores)} 条评分到 DynamoDB...")
    with table.batch_writer() as batch:
        for score in all_scores:
            item = _float_to_decimal(score)
            item["pk"] = f"{score['seller_id']}#{score['marketplace_id']}"
            item["sk"] = f"{score['asin']}#{score['date']}"
            batch.put_item(Item=item)

    print(f"  DynamoDB 上传完成")


# ── S3 ────────────────────────────────────────────────────────────────────

def _create_s3_bucket(s3: Any) -> None:
    """创建 S3 桶（如不存在）"""
    try:
        s3.head_bucket(Bucket=S3_BUCKET)
        print(f"  S3 桶 '{S3_BUCKET}' 已存在")
        return
    except ClientError as e:
        error_code = int(e.response["Error"]["Code"])
        if error_code != 404:
            raise

    print(f"  创建 S3 桶 '{S3_BUCKET}'...")
    # us-east-1 不需要 LocationConstraint
    if REGION == "us-east-1":
        s3.create_bucket(Bucket=S3_BUCKET)
    else:
        s3.create_bucket(
            Bucket=S3_BUCKET,
            CreateBucketConfiguration={"LocationConstraint": REGION},
        )
    print(f"  S3 桶 '{S3_BUCKET}' 创建完成")


def upload_raw_to_s3() -> None:
    """上传原始指标数据到 S3"""
    s3 = boto3.client("s3", region_name=REGION)
    _create_s3_bucket(s3)

    # 上传 ASIN 资料
    profiles_path = RAW_DIR / "asin_profiles.json"
    s3.upload_file(str(profiles_path), S3_BUCKET, "raw/asin_profiles.json")
    print(f"  上传 asin_profiles.json → s3://{S3_BUCKET}/raw/")

    # 上传每日指标
    daily_files = list(RAW_DIR.glob("*_daily.json"))
    print(f"  上传 {len(daily_files)} 个每日指标文件...")
    for fp in daily_files:
        s3.upload_file(str(fp), S3_BUCKET, f"raw/{fp.name}")
    print(f"  每日指标上传完成")

    # 上传汇总
    summary_path = RAW_DIR / "all_asins_daily.json"
    if summary_path.exists():
        s3.upload_file(str(summary_path), S3_BUCKET, "raw/all_asins_daily.json")
        print(f"  上传汇总数据")


def upload_benchmarks_to_s3() -> None:
    """上传基准数据到 S3"""
    s3 = boto3.client("s3", region_name=REGION)

    for fp in BENCHMARK_DIR.glob("*.json"):
        s3.upload_file(str(fp), S3_BUCKET, f"benchmarks/{fp.name}")
        print(f"  上传 {fp.name} → s3://{S3_BUCKET}/benchmarks/")

    print(f"  基准数据上传完成")


def upload_knowledge_to_s3() -> None:
    """上传知识库文档到 S3"""
    s3 = boto3.client("s3", region_name=REGION)

    if not KNOWLEDGE_DIR.exists():
        print(f"  知识库目录不存在: {KNOWLEDGE_DIR}")
        return

    md_files = list(KNOWLEDGE_DIR.glob("*.md"))
    print(f"  上传 {len(md_files)} 个知识库文档...")
    for fp in md_files:
        s3.upload_file(str(fp), S3_BUCKET, f"knowledge_docs/{fp.name}")
        print(f"    {fp.name}")

    print(f"  知识库文档上传完成")


# ── 主流程 ────────────────────────────────────────────────────────────────

def main() -> None:
    print("=" * 50)
    print("ASIN 健康度数据上传")
    print("=" * 50)

    print("\n[1/4] 上传评分到 DynamoDB...")
    upload_scores_to_dynamodb()

    print("\n[2/4] 上传原始指标到 S3...")
    upload_raw_to_s3()

    print("\n[3/4] 上传基准数据到 S3...")
    upload_benchmarks_to_s3()

    print("\n[4/4] 上传知识库文档到 S3...")
    upload_knowledge_to_s3()

    print("\n" + "=" * 50)
    print("全部上传完成！")
    print(f"  DynamoDB 表: {DYNAMODB_TABLE}")
    print(f"  S3 桶: {S3_BUCKET}")
    print("=" * 50)


if __name__ == "__main__":
    main()
