"""ASIN 健康度分析平台 — 完整架构图"""
from diagrams import Diagram, Cluster, Edge
from diagrams.aws.compute import EKS
from diagrams.aws.database import Dynamodb
from diagrams.aws.network import CloudFront, ALB, Route53
from diagrams.aws.storage import S3
from diagrams.aws.ml import Bedrock
from diagrams.aws.security import ACM
from diagrams.onprem.client import User
from diagrams.programming.framework import React, FastAPI
from diagrams.custom import Custom

graph_attr = {
    "bgcolor": "#1a1b23",
    "fontcolor": "white",
    "fontsize": "14",
    "pad": "0.5",
}

node_attr = {
    "fontcolor": "white",
    "fontsize": "11",
}

edge_attr = {
    "color": "#888888",
    "fontcolor": "#cccccc",
    "fontsize": "10",
}

with Diagram(
    "ASIN 智能健康度分析平台",
    filename="/home/ec2-user/.openclaw/media/asin_arch",
    show=False,
    direction="TB",
    graph_attr=graph_attr,
    node_attr=node_attr,
    edge_attr=edge_attr,
):
    user = User("用户")
    
    with Cluster("AWS Cloud", graph_attr={"bgcolor": "#222333", "fontcolor": "#aaaaff"}):
        dns = Route53("Route 53\nasin.chinabjalex.com")
        cdn = CloudFront("CloudFront\nHTTPS + 缓存")
        cert = ACM("ACM 证书\nSSL/TLS")
        
        with Cluster("EKS Cluster (alex-test)", graph_attr={"bgcolor": "#223322", "fontcolor": "#aaffaa"}):
            alb = ALB("ALB\nHTTPS:443")
            
            with Cluster("Pod: asin-health-platform", graph_attr={"bgcolor": "#2a2a3a", "fontcolor": "#ccccff"}):
                frontend = React("React SPA\nDashboard / 诊断")
                api = FastAPI("FastAPI\nREST API")
            
        with Cluster("AI Layer", graph_attr={"bgcolor": "#332222", "fontcolor": "#ffaaaa"}):
            bedrock = Bedrock("Amazon Bedrock\nSonnet 4.6 / Nova Pro")
        
        with Cluster("Data Layer", graph_attr={"bgcolor": "#222233", "fontcolor": "#aaaaff"}):
            ddb = Dynamodb("DynamoDB\n评分数据")
            s3 = S3("S3\n指标/基准/知识库")
    
    # Flow
    user >> Edge(label="HTTPS") >> dns >> cdn
    cdn >> Edge(label="HTTPS:443") >> alb >> api
    api >> Edge(label="静态文件") >> frontend
    api >> Edge(label="Agent 调用") >> bedrock
    api >> Edge(label="评分查询") >> ddb
    api >> Edge(label="指标/知识库") >> s3
    cert - cdn

