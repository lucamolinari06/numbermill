# Local coding delegation

For a small, independent coding change, you may ask the loaded local LM Studio
model for a proposed patch before implementing it yourself. Use
`scripts/delegate_task.py` with a focused task and only the project-relative
files needed for context. The helper returns a proposed diff and does not write
to project files; inspect it, verify the relevant code yourself, and apply only
changes that fit the project.

LM Studio is served locally at `http://127.0.0.1:1234/v1`; the default model is
`prism-ml/bonsai-27b`. Start the API server if needed with:

```powershell
& "$env:USERPROFILE\.lmstudio\bin\lms.exe" server start --port 1234 --bind 127.0.0.1
```

Example:

```powershell
.\.venv\Scripts\python.exe scripts\delegate_task.py --task "Add a helper that clamps a number to a range" --files computation.py
```

Use `--model` to select another loaded model and `--base-url` if the local
server uses a different address. Never send project files to a remote service
as part of this workflow.
