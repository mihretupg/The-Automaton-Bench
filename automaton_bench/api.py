from __future__ import annotations

from pathlib import Path
from tempfile import NamedTemporaryFile

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from automaton_bench.graph import run_audit
from automaton_bench.observability import bootstrap_runtime

bootstrap_runtime()

app = FastAPI(title="Automaton Bench API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/audit")
async def audit_repository(
    repository: str = Form(...),
    pdf_report: UploadFile = File(...),
) -> dict:
    suffix = Path(pdf_report.filename or "report.pdf").suffix or ".pdf"
    temp_path: str | None = None
    try:
        with NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
            content = await pdf_report.read()
            temp_file.write(content)
            temp_path = temp_file.name

        report = run_audit(repository=repository, pdf_report_path=temp_path)
        return report.model_dump(mode="json")
    except (FileNotFoundError, NotADirectoryError, RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - server safety net
        raise HTTPException(status_code=500, detail=f"Audit failed: {exc}") from exc
    finally:
        if temp_path:
            path = Path(temp_path)
            if path.exists():
                path.unlink()


def main() -> None:
    import uvicorn

    uvicorn.run("automaton_bench.api:app", host="0.0.0.0", port=8000, reload=False)


if __name__ == "__main__":
    main()
