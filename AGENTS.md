# AGENTS.md — Voice Agent

Compact repo guidance for future OpenCode sessions. Prefer executable source over stale prose.

## Non-Negotiable Runtime Rules

- Run Python with the repo venv: `.venv/bin/python ...` and `.venv/bin/pip ...`; do not use system `python3` for repo scripts.
- Start commands from repo root: `/home/tyler/voice-agent`.
- Ollama must be reachable at `http://localhost:11434` before benchmark or voice-loop tests.
- Default verified model is `qwen2.5:1.5b`; pull it with `ollama pull qwen2.5:1.5b` if missing.
- Kokoro paths are currently hardcoded in code/tests:
  - model: `/home/tyler/kokoro-onnx/kokoro-v1.0.onnx`
  - voices: `/home/tyler/kokoro-onnx/voices-v1.0.bin`

## High-Value Commands

```bash
# run core local voice loop
.venv/bin/python baseline_loop.py

# run supervisor terminal UI
.venv/bin/python supervisor.py

# benchmark all tiers / specific tier / verbose
.venv/bin/python benchmark.py
.venv/bin/python benchmark.py --tier 3
.venv/bin/python benchmark.py --verbose

# hardware detection + SMB install/update/backup flows
./scripts/detect_hardware.sh
./install.sh
./update.sh
./scripts/backup_config.sh
./scripts/restore_config.sh latest

# Docker stack; verify compose paths before assuming it is production-ready
docker compose up -d
docker compose logs -f
docker compose down
```

## Expected Verification Results

- Full benchmark currently expects **19/20 passing**.
- The known failing test is `Noisy Environment STT`; it needs recorded fixtures matching `logs/noisy_*.wav`.
- LangGraph may emit a deprecation warning about `allowed_objects`; it is cosmetic unless behavior changes.
- TTS first run may be slower due to Kokoro/ONNX warmup.

## Architecture Notes Agents Usually Miss

- `baseline_loop.py` is the real local entrypoint: mic → energy VAD → Faster-Whisper → Ollama → Kokoro-ONNX → speaker.
- `VoiceConfig` in `baseline_loop.py` is the current config source for sample rate, VAD thresholds, model name, timeouts, and hardcoded Kokoro paths.
- `benchmark.py` has its own constants (`OLLAMA_MODEL`, Kokoro paths); keep them in sync with `baseline_loop.py` when changing model/runtime defaults.
- `langgraph_agent/` is orchestration/state plumbing, not the primary runtime path for the baseline loop.
- `sip_bridge.py` is backend scaffolding for Asterisk/FreePBX integration; it imports without `pjsua2` but real SIP behavior still needs a real Asterisk/FreePBX test.
- `pii_handler.py`, `failover_test.py`, `logs/sla_targets.json`, and `logs/audit.jsonl` are part of the compliance/ops story and are referenced by benchmarks.

## Deployment / Packaging Gotchas

- `install.sh` and docs mention hosted installer URLs, but no real hosted URL is configured in this repo yet.
- `docker-compose.yml` mounts `./models`, `./logs`, and `./data`; model files must exist or be supplied separately.
- Compose exposes `7880` both for `voice-agent` and `livekit`; check for port conflicts before running the full stack.
- The compose healthcheck inside `voice-agent` currently checks `localhost:11434`; inside Docker, Ollama is the `ollama` service, so verify/fix before relying on container health.
- SIP libraries such as `pjsua2` are optional and not installed by default; real SIP behavior needs PJSIP prerequisites plus a real Asterisk/FreePBX test.

## Workflow Conventions

- Test before committing; for most code changes run at least the relevant benchmark tier, and full `benchmark.py --verbose` for runtime/packaging changes.
- Commit units should be coherent stories/features. Existing history uses messages like `Story N: Title` and descriptive feature commits.
- Do not commit generated/local artifacts: `.venv/`, `.pre_restore_backup_*.tar.gz`, logs, downloaded models, or local backup tarballs.
- If docs conflict with code/scripts, trust code/scripts and update docs rather than preserving stale instructions.

## Important Files

- `baseline_loop.py` — core local voice pipeline and runtime config.
- `benchmark.py` — 20-test, 5-tier verification suite.
- `install.sh`, `update.sh`, `scripts/detect_hardware.sh`, `scripts/backup_config.sh`, `scripts/restore_config.sh` — SMB backend packaging operations.
- `Dockerfile`, `docker-compose.yml` — container packaging; review gotchas above before demo/deploy.
- `docs/ARCHITECTURE.md`, `docs/DEPLOYMENT.md`, `README.md` — human-facing docs, may lag code.
