from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import uvicorn
import uuid
import json
import threading

# 导入 main.py 中的相关图定义与变量
from main import graph_app

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 提供 frontend 静态文件
app.mount("/static", StaticFiles(directory="frontend"), name="static")

sessions = {}

class RunData(BaseModel):
    question: str
    truth: str

class HumanDecision(BaseModel):
    decision: str  # e.g., "Manual_Confirmed_Match" or "Manual_Overruled_Mismatch"

@app.get("/")
def get_ui():
    with open("frontend/index.html", "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())

@app.post("/api/run")
def start_run(data: RunData):
    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}
    
    initial_state = {
        "question_id": f"q_{thread_id[:4]}",
        "question_context": data.question,
        "ground_truth": data.truth
    }
    
    sessions[thread_id] = {
        "status": "running",
        "nodes": {
            "__start__": {"status": "success", "data": initial_state}
        },
        "state": initial_state
    }
    
    def run_graph():
        try:
            sessions[thread_id]["nodes"]["type_classifier"] = {"status": "executing"}
            # 通过 generator 一步步执行
            for update in graph_app.stream(initial_state, config=config, stream_mode="updates"):
                for node_name, node_update in update.items():
                    sessions[thread_id]["nodes"][node_name] = {"status": "success", "data": node_update}
                    sessions[thread_id]["state"].update(node_update)
            
            # 判断是否被人工审核打断
            state_info = graph_app.get_state(config)
            needs_hitl = state_info.next and "human_review" in state_info.next
            if needs_hitl:
                sessions[thread_id]["status"] = "blocked"
                sessions[thread_id]["nodes"]["human_review"] = {"status": "blocked", "data": {"message": "Waiting for manual review..."}}
            else:
                sessions[thread_id]["status"] = "finished"
                sessions[thread_id]["nodes"]["__end__"] = {"status": "success"}

        except Exception as e:
            sessions[thread_id]["status"] = "error"
            sessions[thread_id]["error"] = str(e)
            
    threading.Thread(target=run_graph, daemon=True).start()
    return {"thread_id": thread_id}

@app.get("/api/status/{thread_id}")
def get_status(thread_id: str):
    if thread_id not in sessions:
        return JSONResponse(status_code=404, content={"error": "Session not found"})
        
    import main
    if thread_id in main.streaming_store:
        # 如果代码生成器节点尚未写入最终结果，则向其中注入当前的流式文本
        if "code_generator" in sessions[thread_id]["nodes"]:
            node_info = sessions[thread_id]["nodes"]["code_generator"]
            if node_info.get("status") == "executing" or "generated_code" not in node_info.get("data", {}):
                node_info["data"] = {"streaming_content": main.streaming_store[thread_id]}
                
    return sessions[thread_id]

@app.post("/api/resume/{thread_id}")
def resume_run(thread_id: str, data: HumanDecision):
    if thread_id not in sessions:
        return JSONResponse(status_code=404, content={"error": "Session not found"})
        
    session = sessions[thread_id]
    if session["status"] != "blocked":
        return JSONResponse(status_code=400, content={"error": "Session is not blocked"})
        
    config = {"configurable": {"thread_id": thread_id}}
    
    # 更新 state
    graph_app.update_state(config, {"final_decision": data.decision})
    
    session["status"] = "running"
    session["nodes"]["human_review"] = {"status": "success", "data": {"final_decision": data.decision}}
    
    def resume_graph():
        try:
            for update in graph_app.stream(None, config=config, stream_mode="updates"):
                for node_name, node_update in update.items():
                    sessions[thread_id]["nodes"][node_name] = {"status": "success", "data": node_update}
                    sessions[thread_id]["state"].update(node_update)
            
            sessions[thread_id]["status"] = "finished"
            sessions[thread_id]["nodes"]["__end__"] = {"status": "success"}
        except Exception as e:
            sessions[thread_id]["status"] = "error"
            sessions[thread_id]["error"] = str(e)
            
    threading.Thread(target=resume_graph, daemon=True).start()
    return {"status": "success"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)
