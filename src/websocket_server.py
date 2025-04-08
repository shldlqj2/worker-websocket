import asyncio
import websockets
import json
import logging
from src.engine import vLLMEngine, OpenAIvLLMEngine
from src.utils import JobInput

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("WebSocketServer")

class WebSocketServer:
    def __init__(self, engine, host, port):
        self.engine = engine
        self.host = host
        self.port = port
        self.server = None
        
        self.active_connections = {}
        self.active_tasks = {}
        self.job_complete_events={}

        self.generation_task = None
        self.connection_complete = asyncio.Event()
        self.all_tasks_complete = asyncio.Event()
        self.is_shutting_down = False

    async def start_generation(self, job):
        """vLLM 생성 작업 시작"""
        job_id = JobInput(job["input"]).request_id

        task = asyncio.create_task(
            self._handle_generation(job,job_id)
        )
        self.active_tasks[job_id] = task
        task.add_done_callback(lambda _: self.cleanup_task(job_id))
        
        logger.info(f"{job_id}추론시작")

    def cleanup_task(self, job_id):
        if job_id in self.active_tasks:
            del self.active_tasks[job_id]
        
        if not self.active_tasks:
            self.all_tasks_complete.set()
            if not self.active_connections and not self.is_shutting_down:
                self.is_shutting_down = True
                logger.info("모든 작업 완료, 서버 종료 시작")
                asyncio.create_task(self.shutdown())


        logger.info(f"{job_id} 작업 정리 완료, 남은 작업: {len(self.active_tasks)}")
        

    async def _handle_generation(self, prompt, job_id):
        """실제 텍스트 생성 처리"""
        try:
            connected_clients = [ws for ws, jid in self.active_connections.items() if jid == job_id]

            job_input = JobInput(prompt["input"])
            logger.info(f"JobInput처리완료")
            results_generator = self.engine.generate(job_input)
            
            #job_id에 해당하는 client에게만 결과 전송해야함
            async for token in results_generator:
                for websocket in connected_clients.copy():
                    if websocket in self.active_connections:
                        try:
                            await websocket.send(json.dumps({
                                "token": token,
                                "finished": False
                            }))
                        except websockets.exceptions.ConnectionClosed:
                            if websocket in self.active_connections:
                                del self.active_connections[websocket]
                            connected_clients.remove(websocket)

            # 완료 신호 전송
            for websocket in connected_clients.copy():
                if websocket in self.active_connections:
                    await websocket.send(json.dumps({"finished": True}))
                    logger.info(f"작업 {job_id}의 완료 신호 전송완료")
                
            
        except Exception as e:
            logger.error(f"생성 오류: 작업 {job_id}: {str(e)}")
            for websocket in connected_clients.copy():
                if websocket in self.active_connections:
                    try:
                        await websocket.send(json.dumps({"error": str(e), "finished": True}))
                    except:
                        pass
                    logger.info(f"작업 {job_id}의 오류 신호 전송완료")
            

    async def handle_client(self, websocket):
        """클라이언트 연결 처리"""
        self.active_connections[websocket] = None
        self.connection_complete.set()
        try:
            # 클라이언트로부터 종료 신호 대기
            async for message in websocket:
                data = json.loads(message)
                if data.get("command") == "start_job":
                    if "job" in data:
                        job_id = await self.start_generation(data["job"])
                        self.active_connections[websocket] = job_id
                        await websocket.send(json.dumps({
                            "status": "작업 시작",
                            "job_id": job_id
                        }))

                    elif data.get("command") == "shutdown":
                        await websocket.send(json.dumps({
                            "status": "종료"
                        }))
                        break
                        logger.info(f"Websocket 서버 종료")
                    
        except websockets.exceptions.ConnectionClosed:
            pass

        finally:
            if websocket in self.active_connections:
                del self.active_connections[websocket]
            logger.info(f"클라이언트 종료 완료, 남은 연결: {len(self.active_connections)}")
            

    async def start(self):
        """서버 시작"""
        self.server = await websockets.serve(
            self.handle_client,
            self.host,
            self.port
        )
        logger.info(f"서버 시작: {self.host}:{self.port}")

    async def shutdown(self):
        """그레이스풀 종료"""
        logger.info(f"websocket_server 종료 함수 실행")

        await asyncio.wait_for(self.all_tasks_complete.wait())
        
        for job_id, task in self.active_tasks.copy().items():
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
                if job_id in self.job_complete_events:
                    self.job_complete_events[job_id].set()
        
        if self.server:
            self.server.close()
            await self.server.wait_closed()
            logger.info(f"Websocket 서버 종료 완료")

    async def wait_for_job_completion(self, job_id):
        """특정 작업의 완료를 기다림"""
        if job_id in self.job_complete_events:
            await self.job_complete_events[job_id].wait()
            return True
        return False



# import asyncio
# import websockets
# import json
# import logging
# from src.engine import vLLMEngine, OpenAIvLLMEngine
# from src.utils import JobInput

# logging.basicConfig(level=logging.INFO)
# logger = logging.getLogger("WebSocketServer")

# class WebSocketServer:
#     def __init__(self, engine, host, port):
#         self.engine = engine
#         self.host = host
#         self.port = port
#         self.server = None
#         self.active_connections = set()
#         self.generation_task = None
#         self.generation_complete = asyncio.Event()
#         self.connection_complete = asyncio.Event()

#     async def start_generation(self, job):
#         """vLLM 생성 작업 시작"""
        
#         self.generation_task = asyncio.create_task(
#             self._handle_generation(job)
#         )
#         logger.info(f"추론시작")

#     async def _handle_generation(self, prompt):
#         """실제 텍스트 생성 처리"""
#         try:
#             job_input = JobInput(prompt["input"])
#             results_generator = self.engine.generate(job_input)
#             async for token in results_generator:
#                 # 모든 연결된 클라이언트에게 전송
#                 for websocket in self.active_connections.copy():
#                     try:
#                         await websocket.send(json.dumps({
#                             "token": token,
#                             "finished": False
#                         }))
#                     except websockets.exceptions.ConnectionClosed:
#                         self.active_connections.remove(websocket)
            
#             # 완료 신호 전송
#             for websocket in self.active_connections.copy():
#                 await websocket.send(json.dumps({"finished": True}))
#                 logger.info(f"완료 신호 전송완료")
            
#         except Exception as e:
#             logger.error(f"생성 오류: {str(e)}")
            

#     async def handle_client(self, websocket):
#         """클라이언트 연결 처리"""
#         self.active_connections.add(websocket)
#         self.connection_complete.set()
#         try:
#             # 클라이언트로부터 종료 신호 대기
#             async for message in websocket:
#                 data = json.loads(message)
#                 if data.get("command") == "shutdown":
#                     await websocket.send(json.dumps({
#                         "status": "종료 중"
#                     }))
#                     logger.info(f"websocket_server 종료 요청 수신")
                    
#         except websockets.exceptions.ConnectionClosed:
#             pass
#         finally:
#             self.active_connections.remove(websocket)
#             logger.info(f"토큰 생성 완료")
#             await self.shutdown()

#     async def start(self):
#         """서버 시작"""
#         self.server = await websockets.serve(
#             self.handle_client,
#             self.host,
#             self.port
#         )
#         logger.info(f"Websocket 서버 시작: {self.host}:{self.port}")

#     async def shutdown(self):
#         """그레이스풀 종료"""
#         logger.info(f"websocket_server 종료 함수 실행")
#         if self.generation_task and not self.generation_task.done():
#             self.generation_task.cancel()
#             try:
#                 await self.generation_task
#             except asyncio.CancelledError:
#                 pass
#         self.generation_complete.set()


#         if self.server:
#             self.server.close()
#             await self.server.wait_closed()


# import asyncio
# import websockets
# import json
# import logging
# from utils import JobInput

# logging.basicConfig(level=logging.INFO)
# logger = logging.getLogger("websocket_server")

# class WebSocketServer:
#     def __init__(self, engine, host="0.0.0.0", port=8765):
#         """
#         WebSocket 서버 초기화
        
#         Args:
#             engine: vLLM 엔진 인스턴스
#             host: 서버 호스트 주소
#             port: 서버 포트
#         """
#         self.engine = engine
#         self.host = host
#         self.port = port
#         self.server = None
#         self.active_connections = set()
    
#     async def handle_client(self, websocket, path):
#         """
#         클라이언트 연결 처리
#         """
#         self.active_connections.add(websocket)
#         try:
#             logger.info(f"클라이언트 연결됨: {websocket.remote_address}")
            
#             async for message in websocket:
#                 try:
#                     data = json.loads(message)
                    
#                     # "shutdown" 명령 처리
#                     if data.get("command") == "shutdown":
#                         logger.info("종료 명령 수신됨")
#                         await websocket.send(json.dumps({"status": "shutting_down"}))
#                         await self.shutdown()
#                         return
                    
#                     # 프롬프트 처리
#                     input_data = data.get("input")
#                     if input_data:
#                         from utils import JobInput
                        
#                         # JobInput 클래스를 사용하여 입력 처리
#                         job_input = JobInput(input_data)
#                         logger.info(f"프롬프트 수신: {str(job_input.llm_input)[:50]}...")
                        
#                         # vLLM 엔진을 사용해 응답 생성
#                         results_generator = self.engine.generate(job_input)
#                         async for batch in results_generator:
#                             if isinstance(batch, dict) and "text" in batch:
#                                 await websocket.send(json.dumps({"token": batch["text"], "finished": False}))
#                             elif isinstance(batch, str):
#                                 await websocket.send(json.dumps({"token": batch, "finished": False}))
#                             else:
#                                 # 다른 형식의 응답 처리
#                                 token = str(batch)
#                                 await websocket.send(json.dumps({"token": token, "finished": False}))
                        
#                         # 완료 메시지 전송
#                         await websocket.send(json.dumps({"finished": True}))

                        
#                 except json.JSONDecodeError:
#                     await websocket.send(json.dumps({
#                         "error": "잘못된 JSON 형식입니다."
#                     }))
#                 except Exception as e:
#                     logger.error(f"메시지 처리 중 오류 발생: {str(e)}")
#                     await websocket.send(json.dumps({
#                         "error": f"메시지 처리 중 오류 발생: {str(e)}"
#                     }))
        
#         except websockets.exceptions.ConnectionClosed:
#             logger.info(f"클라이언트 연결 종료됨: {websocket.remote_address}")
#         finally:
#             self.active_connections.remove(websocket)
    
#     async def start(self):
#         """
#         WebSocket 서버 시작
#         """
#         self.server = await websockets.serve(
#             self.handle_client, 
#             self.host, 
#             self.port
#         )
        
#         logger.info(f"WebSocket 서버가 {self.host}:{self.port}에서 시작되었습니다")
        
#         # 서버 실행 유지
#         await self.server.wait_closed()
    
#     async def shutdown(self):
#         """
#         서버 종료
#         """
#         if self.server:
#             # 모든 활성 연결 종료
#             for websocket in self.active_connections.copy():
#                 await websocket.close()
            
#             self.server.close()
#             await self.server.wait_closed()
#             logger.info("WebSocket 서버가 종료되었습니다")
