.PHONY: dev api dashboard install

install:
	cd rga-copilot && .venv/bin/pip install fastapi "uvicorn[standard]" python-multipart httpx pytest-asyncio
	cd dashboard && npm install

api:
	cd api && ../rga-copilot/.venv/bin/uvicorn main:app --reload --port 8000

dashboard:
	cd dashboard && npm run dev

dev:
	@trap 'kill 0' SIGTERM SIGINT; \
	$(MAKE) api & \
	$(MAKE) dashboard & \
	wait
