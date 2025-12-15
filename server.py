import subprocess
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

APP_DIR = Path(__file__).resolve().parent
INDEX_HTML = APP_DIR / "index.html"
TMP_OUT = APP_DIR / "_ipa_out.txt"

app = FastAPI(title="IPA Català Local (WyZeR)")


class IPARequest(BaseModel):
    text: str
    voice: str = "ca"
    keep_stress: bool = True


@app.get("/", response_class=HTMLResponse)
def home():
    if not INDEX_HTML.exists():
        return HTMLResponse("<h1>Falta index.html</h1>", status_code=500)
    return HTMLResponse(INDEX_HTML.read_text(encoding="utf-8"))


@app.post("/api/ipa")
def ipa(req: IPARequest):
    text = (req.text or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="Text buit")

    # Escrivim sempre a fitxer per evitar UnicodeEncodeError (cp1252) a Windows
    try:
        if TMP_OUT.exists():
            TMP_OUT.unlink()
    except Exception:
        pass

    cmd = [
        "espeak-phonemizer",
        "-v", req.voice,
        "-p", "",              # separador fonemes
        "-w", "",              # separador paraules
        "-o", str(TMP_OUT),    # sortida a fitxer (UTF-8)
        text,
    ]
    if not req.keep_stress:
        cmd.insert(1, "--no-stress")

    try:
        p = subprocess.run(cmd, capture_output=True, text=True, check=False)
    except FileNotFoundError:
        raise HTTPException(
            status_code=500,
            detail="No trobo 'espeak-phonemizer'. Activa la venv i reinstal·la requirements.",
        )

    if p.returncode != 0:
        err = (p.stderr or "").strip()
        raise HTTPException(status_code=500, detail=f"espeak-phonemizer error: {err or 'unknown'}")

    if not TMP_OUT.exists():
        raise HTTPException(status_code=500, detail="No s'ha generat el fitxer de sortida IPA (_ipa_out.txt).")

    ipa_text = TMP_OUT.read_text(encoding="utf-8").strip()
    ipa_text = ipa_text.replace("\u200b", "").replace(" ", "")

    if not ipa_text:
        raise HTTPException(status_code=500, detail="Sortida IPA buida")

    return {"ipa": ipa_text}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="127.0.0.1", port=8000, reload=False)
