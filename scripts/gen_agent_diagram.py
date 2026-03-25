"""Agent 架构图 — Multi-Agent 协作关系"""
from diagrams import Diagram, Cluster, Edge
from diagrams.aws.ml import Bedrock
from diagrams.aws.database import Dynamodb
from diagrams.aws.storage import S3
from diagrams.programming.framework import FastAPI
from diagrams.onprem.client import User
from diagrams.generic.compute import Rack

graph_attr = {"bgcolor": "#1a1b23", "fontcolor": "white", "fontsize": "14", "pad": "0.5"}
node_attr = {"fontcolor": "white", "fontsize": "10"}
edge_attr = {"color": "#888888", "fontcolor": "#cccccc", "fontsize": "9"}

with Diagram(
    "Multi-Agent 架构",
    filename="/home/ec2-user/.openclaw/media/asin_agent_arch",
    show=False,
    direction="TB",
    graph_attr=graph_attr,
    node_attr=node_attr,
    edge_attr=edge_attr,
):
    user = User("用户")
    api = FastAPI("FastAPI API")
    
    with Cluster("Supervisor Agent\n(Sonnet 4.6)", graph_attr={"bgcolor": "#332244", "fontcolor": "#ccaaff"}):
        supervisor = Rack("协调路由\n任务分解")
    
    with Cluster("Sub-Agents", graph_attr={"bgcolor": "#223344", "fontcolor": "#aaccff"}):
        with Cluster("Sonnet 4.6", graph_attr={"bgcolor": "#2a3344"}):
            root_cause = Rack("根因分析\nAgent")
            action = Rack("行动建议\nAgent")
            competitor = Rack("竞品对标\nAgent")
        
        with Cluster("Nova Pro", graph_attr={"bgcolor": "#2a4433"}):
            score = Rack("评分查询\nAgent")
            knowledge = Rack("知识检索\nAgent")
    
    with Cluster("Tools (7个)", graph_attr={"bgcolor": "#333322", "fontcolor": "#ffffaa"}):
        tools = Rack("get_asin_score\nget_asin_metrics\nget_metrics_trend\nget_score_summary\nlist_asins_by_health\nget_category_benchmark\nsearch_knowledge")

    with Cluster("Data Sources", graph_attr={"bgcolor": "#222233", "fontcolor": "#aaaaff"}):
        ddb = Dynamodb("DynamoDB")
        s3 = S3("S3")
        bedrock = Bedrock("Bedrock")
    
    user >> api >> supervisor
    supervisor >> Edge(label="Agents as Tools") >> [score, root_cause, action, competitor, knowledge]
    
    api >> Edge(label="诊断(并行)", style="dashed") >> root_cause
    api >> Edge(label="诊断(并行)", style="dashed") >> competitor
    api >> Edge(label="诊断(串行)", style="dashed") >> action
    
    [score, root_cause, action, competitor, knowledge] >> tools
    tools >> ddb
    tools >> s3
    [root_cause, action, competitor, score, knowledge] >> bedrock

