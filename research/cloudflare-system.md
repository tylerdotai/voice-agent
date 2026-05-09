# Voiceline on Cloudflare — Full System Analysis

_Created: 2026-05-09_

---

## What We're Building

A commercial real-time voice AI agent product for DFW home services contractors, deployed on Cloudflare's edge. Customers call a phone number → Cloudflare Durable Object picks up → streams voice pipeline (VAD → STT → LLM → TTS) → caller talks to AI receptionist.

---

## Why Cloudflare Is the Right Infrastructure

| Requirement | Cloudflare Delivers |
|-------------|---------------------|
| Real-time voice (<1s latency) | Durable Objects + WebSocket, edge-near |
| STT + TTS + LLM | Workers AI binding, zero external API keys needed |
| Multi-tenant per-customer isolation | One Durable Object per customer account |
| Persistence across calls | SQLite in Durable Objects |
| Scale from 1 to 10,000 customers | Workers auto-scales, pay per request |
| Cheap proto/minimal cost | $5/mo base + usage, no servers to manage |
| Agent-as-customer provisioning | Autonomous Stripe onboarding (future) |

---

## Core Stack

### `@cloudflare/voice` Package

Cloudflare's official voice agent framework. The real find.

```
npm create cloudflare@latest voiceline-agent -- --template cloudflare/agents-starter
cd voiceline-agent
npm install @cloudflare/voice
```

Built on:
- **Agents SDK** — Durable Object wrapper with SQLite, WebSocket, scheduling
- **`withVoice` mixin** — wraps an `Agent` class with full voice pipeline
- **`useVoiceAgent` React hook** — browser-side mic capture + audio playback in ~10 lines

### Voice Pipeline Architecture

```
Caller phone
    ↓
Telnyx / Plivo (DID → WebSocket → Cloudflare Worker)
    ↓
Durable Object (MyVoiceAgent)
    ↓
┌─────────────────────────────────────────────────────────┐
│  1. VAD: smart-turn-v2 (@cf/pipecat-ai/smart-turn-v2) │  ← server-side confirms end-of-speech
│  2. STT: Deepgram Nova 3 (@cf/deepgram/nova-3)         │  ← Workers AI binding
│  3. LLM: streamText() via workers-ai-provider          │  ← can swap models
│  4. TTS: Deepgram Aura (@cf/deepgram/aura-1)           │  ← streaming per-sentence
│  5. Conversation persistence: SQLite in DO             │
└─────────────────────────────────────────────────────────┘
    ↓
Caller hears response in <1s while LLM is still generating
```

Key features:
- **Streaming TTS** — sentences synthesized and sent as audio while LLM is still outputting
- **Interruption support** — caller can "speak over" agent mid-sentence, triggers `abortSignal`
- **Server-side VAD** — validates end-of-speech after client-side silence detection
- **SQLite persistence** — messages survive DO restarts, agent remembers prior conversations
- **`afterTranscribe` / `beforeSynthesize` hooks** — filter noise, adjust pronunciation

### Example Server (from CF docs)

```typescript
import { Agent, routeAgentRequest, type Connection } from "agents";
import { withVoice, WorkersAIFluxSTT, WorkersAITTS, type VoiceTurnContext } from "@cloudflare/voice";
import { streamText, tool, stepCountIs } from "ai";
import { createWorkersAI } from "workers-ai-provider";
import { z } from "zod";

const VoiceAgent = withVoice(Agent);

export class VoicelineReceptionist extends VoiceAgent<Env> {
  transcriber = new WorkersAIFluxSTT(this.env.AI);
  tts = new WorkersAITTS(this.env.AI);

  async onTurn(transcript: string, context: VoiceTurnContext) {
    const workersAi = createWorkersAI({ binding: this.env.AI });
    const result = streamText({
      model: workersAi("@cf/meta/llama-3.2-3b-instruct"),  // or @cf/qwen/qwen3-30b-a3b-fp8
      system: "You are a professional AI receptionist for a HVAC contractor...",
      messages: [...context.messages.map(m => ({ role: m.role, content: m.content })), { role: "user", content: transcript }],
      tools: { /* book_appointment, qualify_lead, transfer_to_owner */ },
      stopWhen: stepCountIs(3),
      abortSignal: context.signal,
    });
    return result.textStream;
  }

  async onCallStart(connection: Connection) {
    await this.speak(connection, "Thanks for calling. You've reached [Business Name]. How can I help you today?");
  }
}

export default { fetch: (request, env) => routeAgentRequest(request, env) ?? new Response("Not found", { status: 404 }) };
```

### Third-Party Provider Swap

If we want ElevenLabs + Deepgram instead of Workers AI native:

```typescript
import { ElevenLabsTTS } from "@cloudflare/voice-elevenlabs";
import { DeepgramSTT } from "@cloudflare/voice-deepgram";

export class VoicelineReceptionist extends VoiceAgent {
  transcriber = new DeepgramSTT({ apiKey: this.env.DEEPGRAM_API_KEY });
  tts = new ElevenLabsTTS({ apiKey: this.env.ELEVENLABS_API_KEY, voiceId: "..." });
}
```

---

## Pricing Breakdown

### Base: Workers Paid — $5/month

| Item | Included | Overage |
|------|----------|---------|
| Requests | 10M/mo | $0.30/million |
| CPU time | 30M CPU-ms/mo | $0.02/million CPU-ms |
| Workers KV | 10M reads, 1M writes | $0.50/M reads, $5/M writes |
| Durable Objects | 1M requests, 400K GB-s | $0.15/M requests, $12.50/M GB-s |

Note: WebSocket messages are NOT billed as requests (only the initial Upgrade). So a voice call that lasts 5 minutes and exchanges 200 messages = 1 request (the WebSocket upgrade).

### Workers AI — Billed in Neurons

Requires Workers Paid plan. Free tier: 10,000 neurons/day. Then:

| Model | Neurons/M input | Neurons/M output | Cost/1K calls (est) |
|-------|-----------------|------------------|---------------------|
| `@cf/meta/llama-3.2-1b-instruct` | 2,457 | 18,252 | ~$0.02/1K |
| `@cf/meta/llama-3.2-3b-instruct` | 4,625 | 30,475 | ~$0.04/1K |
| `@cf/meta/llama-3.1-8b-instruct-fp8-fast` | 4,119 | 34,868 | ~$0.05/1K |
| `@cf/mistral/mistral-7b-instruct-v0.1` | 10,000 | 17,300 | ~$0.03/1K |
| `@cf/ibm-granite/granite-3.0-h-micro` | 1,542 | 10,158 | ~$0.01/1K ← cheapest |
| `@cf/qwen/qwen3-30b-a3b-fp8` | 4,625 | 30,475 | ~$0.04/1K |

**STT (Deepgram Nova 3)** and **TTS (Deepgram Aura)** also use Workers AI neurons.

Workers AI is included in the same $0.011/1,000 Neurons rate.

### Estimated Cost Per Customer Call

Voice calls consume neurons for:
1. STT — ~5 sec of audio → ~5,000 neurons (estimate)
2. LLM inference — ~200 token response → ~5,000 neurons
3. TTS — ~150 output tokens → ~15,000 neurons

Total: ~25,000 neurons per average call interaction.

At $0.011/1,000 neurons = **$0.000275 per call interaction**.

At 500 calls/month (Starter tier):
- STT + LLM + TTS neurons: 500 × $0.000275 = **$0.14/mo**
- DO compute (假设 30s per call × 500 = 15,000 GB-s): within 400K included
- **Total AI cost per Starter customer: ~$0.14/mo** — essentially free

At 2,000 calls/month (Pro tier): ~$0.55/mo in AI costs.

This is the killer insight: **AI inference cost per customer is under $1/mo**. The infrastructure arbitrage is massive.

### Durable Objects — Per Customer

One DO = one customer's voice agent. Active when call is in progress, hibernates when idle (no duration charge with WebSocket Hibernation API).

Voice calls use WebSocket, so:
- DO is billed only during active call (request = WebSocket upgrade)
- Hibernation = no duration charge

**Durable Objects Paid plan**: 1M requests/mo, 400K GB-s/mo included.

500 Starter calls/mo → 500 requests, <10,000 GB-s → **$0 in DO charges**.

### Realistic Monthly Cost Estimate

For 100 customers, 500 calls each/month:

| Cost | Calculation | Monthly |
|------|-------------|---------|
| Workers Paid | base | $5.00 |
| 100 DOs (idle) | 100 × $0.15/M requests × 0.001M | $0.015 |
| Workers AI (50K calls) | 50,000 calls × 25K neurons × $0.011/1K | $13.75 |
| KV storage | minimal | ~$0.50 |
| **Total** | | **~$19.25/mo for 100 customers** |

That's **$0.19/customer/month** in direct infrastructure cost. Margin at $79/mo Starter is 99.7%.

---

## Multi-Tenant Architecture

```
Cloudflare Account (Voiceline)
│
├── Workers Namespace: "voiceline-prod"
│   ├── Durable Object: VoicelineDO per customer
│   │   ├── owns WebSocket to caller
│   │   ├── SQLite: conversation history, appointments, leads
│   │   └── env.AI → Workers AI binding
│   │
│   └── Worker: routes incoming PSTN calls → appropriate DO
│
├── R2 Bucket: "voiceline-assets" (greetings, call recordings with consent)
├── D1 Database: "voiceline-meta" (customer accounts, billing, plan)
├── KV Namespace: "voiceline-config" (per-customer settings, greetings)
└── Queues: "voiceline-notifications" (SMS after call, owner alerts)
```

### Customer Provisioning Flow

```
New customer signs up on web
    ↓
Stripe Checkout → payment captured
    ↓
Cloudflare API: create new DO namespace for customer
    ↓
KV: write customer config (business name, greeting, hours, services)
    ↓
Telnyx/Plivo: provision DID, point to Worker WebSocket
    ↓
Worker routes DID → customer's DO
    ↓
"Voiceline is now live!" confirmation email
```

This can be fully autonomous via the Agent-as-Customer with Stripe protocol.

---

## Telephony: Getting Calls In

Cloudflare doesn't provide phone numbers. We need a SIP/TDM provider:

| Provider | Notes |
|----------|-------|
| **Telnyx** | DidForSale alternative, programmable voice, SIP trunking, $0.004/min US |
| **Plivo** | Similar model, $0.0045/min US |
| **Twilio** | Expensive but reliable, $0.01/min US |
| **Bandwidth** | Good for high volume, lower cost at scale |

Flow: DID purchase → SIP trunk → Cloudflare Worker (receives webhook) → Durable Object WebSocket.

For a voice agent, the call comes in via a WebSocket upgrade from the telephony provider to our Worker. The Worker creates/gets the customer's DO, and the DO handles the voice pipeline.

**Important**: Most telephony providers deliver calls as regular HTTP webhooks, not WebSockets. For real-time voice, we need a provider that supports WebSocket or a media server that proxies to WebSocket. Telnyx has a Voice API with WebSocket support. This needs further research.

Alternative: Use a cloud PBX like Twilio Voice that can connect a call to a WebSocket endpoint. Twilio supports `<Response>` with `<Connect><Stream>` to connect a live call to a WebSocket.

---

## Voice Model Strategy

### Option A: Workers AI Native (Cheapest)
- STT: `@cf/deepgram/nova-3` — included in Workers AI
- TTS: `@cf/deepgram/aura-1` — included in Workers AI
- LLM: `@cf/meta/llama-3.2-3b-instruct` or `@cf/qwen/qwen3-30b-a3b-fp8`
- **Cost**: ~$0.000275/call interaction
- **Trade-off**: Quality vs hosted competitors; good enough for home services context

### Option B: Third-Party Best-in-Class
- STT: Deepgram Nova 3 (direct API, $0.004/min audio)
- TTS: ElevenLabs v3 (direct API, $0.30/1K chars)
- LLM: Anthropic Claude via AI Gateway (rate-limited, $3-15/1M tokens)
- **Cost**: ~$0.01-0.05/call interaction
- **Trade-off**: Higher quality, more expensive

### Option C: Hybrid (Recommended for product)
- Starter tier: Workers AI native (cost-first)
- Pro/Business: ElevenLabs + Claude (quality-up)
- Same voice pipeline, swap STT/TTS/LLM at tier level

---

## Real-Time Requirements

| Requirement | Target | Notes |
|-------------|--------|-------|
| Time-to-first-audio | <500ms | LLM + TTS pipeline must be fast |
| Interruption latency | <200ms | Caller speaks → agent stops |
| Total call duration | no limit | Pro/Business = unlimited |
| Concurrent calls | 10K+ | Workers auto-scales |

For real-time voice, the bottleneck is TTS synthesis time. Deepgram Aura on Workers AI is optimized for streaming — sentences go out as they're synthesized, not after full generation. This is critical for the <500ms target.

The `qwen3-30b-a3b-fp8` model from Workers AI would give strong reasoning for appointment booking and lead qualification flows.

---

## Agent-as-Customer (April 30, 2026)

Cloudflare's protocol for agents autonomously creating accounts + deploying:

```
Agent (Voiceline provisioning bot)
    → stripe projects init
    → discovers Voiceline services (DO, Workers AI, KV)
    → provisions new customer namespace
    → deploys customer-configured voice agent
    → registers domain (optional: customer.voiceline.app)
    → Stripe is identity + payment
    → $100/mo spending cap per provider (ours)
```

This means Voiceline could provision new customer instances autonomously. The agent IS the customer from Cloudflare's perspective — no human-ops required to spin up a new customer.

**Spending caps**: Set `$100/month` limit per external provider. If we offer LLM providers, we set their cap.

---

## Voice Provider Integration (Critical Missing Piece Found!)

### Twilio Adapter — `voice-twilio`


Cloudflare ships an **official Twilio adapter**: `@cloudflare/voice-twilio`. This is the bridge that connects phone calls to the voice agent pipeline. This is the missing piece.


```bash
npm install @cloudflare/voice-twilio
```

```typescript
import { Agent, routeAgentRequest } from "agents";
import { withVoice, type VoiceTurnContext } from "@cloudflare/voice";
import { TwilioAdapter } from "@cloudflare/voice-twilio";

const VoiceAgent = withVoice(Agent);

export class VoicelineReceptionist extends VoiceAgent<Env> {
  async onTurn(transcript: string, context: VoiceTurnContext) {
    // Same agent handles both web and phone calls
    return "You said: " + transcript;
  }
}

export default {
  async fetch(request: Request, env: Env) {
    const url = new URL(request.url);
    if (url.pathname === "/twilio") {
      return TwilioAdapter.handleRequest(request, env, "VoicelineReceptionist");
    }
    return (await routeAgentRequest(request, env)) ?? new Response("Not found", { status: 404 });
  }
};
```

**Twilio Console setup** — create a TwiML Bin and attach to a DID:
```xml
<Response>
  <Connect>
    <Stream url="wss://voiceline.your-account.workers.dev/twilio" />
  </Connect>
</Response>
```

**Architecture after adding Twilio:**
```
Caller → Twilio DID → TwiML Stream → wss://voiceline.workers.dev/twilio
    → TwilioAdapter (CF Worker) → VoicelineReceptionist (Durable Object)
    → STT → LLM → TTS → TwilioAdapter → Twilio → Caller speaker
```

The same `VoicelineReceptionist` Durable Object class handles:
- **Web voice** via `useVoiceAgent` React hook
- **Phone calls** via Twilio Media Streams
- **Text chat** via `sendText()`
- All channels share SQLite conversation history, tools, and state

**Note:** TTS output format (MP3 from Deepgram Aura) needs conversion for Twilio. Outbound conversion (MP3 → mulaw) requires an MP3 decoder. Options:
1. Use `beforeSynthesize` hook to convert format
2. Use a TTS provider that outputs mulaw/PCM directly
3. Telnyx TTS has both REST and WebSocket backends, WebSocket mode works on Workers


### Telnyx Integration — `@telnyx/voice-cloudflare`


Official package from Telnyx team: `npm install @telnyx/voice-cloudflare`


Gives `@cloudflare/voice` agents access to:
- **STT**: `TelnyxSTT` — Deepgram Nova 3 engine, real-time
- **TTS**: `TelnyxTTS` — natural HD voices, REST or WebSocket backend
- **PSTN Bridge**: `TelnyxCallBridge` — captures PCM audio from PSTN calls
- **Phone Client**: `TelnyxPhoneClient` — speaks Cloudflare voice protocol directly
- **JWT Endpoint**: `TelnyxJWTEndpoint` — server-side token generation (keeps API key secure)

```typescript
import { TelnyxSTT, TelnyxTTS, TelnyxCallBridge, TelnyxPhoneClient, createTelnyxVoiceConfig } from "@telnyx/voice-cloudflare";

// Use Telnyx STT/TTS with Cloudflare voice agent
export class VoicelineReceptionist extends VoiceAgent<Env> {
  transcriber = new TelnyxSTT({ apiKey: this.env.TELNYX_API_KEY });
  tts = new TelnyxTTS({ apiKey: this.env.TELNYX_API_KEY, voice: "Telnyx.NaturalHD.astra" });
}
```

**Phone call via TelnyxPhoneClient:**
```typescript
// Server: JWT endpoint for auth
const jwt = new TelnyxJWTEndpoint({ apiKey: env.TELNYX_API_KEY, credentialConnectionId: env.TELNYX_CREDENTIAL_CONNECTION_ID });

// Client: WebRTC to PSTN
const telnyx = await createTelnyxVoiceConfig({ jwtEndpoint: "/api/telnyx-token", autoAnswer: true });
const phoneClient = new TelnyxPhoneClient({ transport: new WebSocketVoiceTransport({ agent: "my-agent" }), bridge: telnyx.bridge });
phoneClient.connect();
```

**Key packages from `@telnyx/voice-cloudflare`:**
- `@telnyx/voice-cloudflare/stt` — STT only, no WebRTC dependency
- `@telnyx/voice-cloudflare/tts` — TTS only, no WebRTC dependency
- `@telnyx/voice-cloudflare/telephony` — PSTN bridge, phone client, JWT endpoint


### Provider Comparison for Voiceline

| Feature | Twilio + voice-twilio | Telnyx + voice-cloudflare |
|---------|----------------------|---------------------------|
| PSTN inbound calls | ✅ TwiML Stream to WS | ✅ WebRTC + SIP |
| STT | Deepgram (via adapter) | TelnyxSTT (Deepgram nova-3) |
| TTS | Deepgram Aura | Telnyx NaturalHD |
| Audio format handling | MP3 → mulaw conversion needed | WebSocket mode native on Workers |
| Pricing | $0.008/min (US), $0.002/min streaming | ~$0.004/min US |
| DID cost | ~$1-2/mo per number | ~$0.50-1/mo per number |
| Agent-as-Customer ready | Stripe billing | Stripe billing |

**Recommendation:** Telnyx + `@telnyx/voice-cloudflare` for the PSTN bridge, because:
1. WebSocket TTS backend works natively on Cloudflare Workers (no format conversion)
2. Cheaper per-minute rate
3. Official first-party package
4. Carrier-grade voice infrastructure, not just a webhook bridge

Use Twilio as fallback if Telnyx has coverage gaps in DFW.

### Complete Architecture with Telephony

```
Caller dials +1 (214) XXX-XXXX
    ↓
Telnyx / Twilio (DID + PSTN network)
    ↓
WebSocket stream to Cloudflare Worker (/twilio or /telnyx path)
    ↓
Durable Object: VoicelineReceptionist (one per customer)
    ├── owns WebSocket to caller
    ├── SQLite: conversation history, appointments, leads
    ├── STT: TelnyxSTT or WorkersAIFluxSTT
    ├── LLM: streamText() via workers-ai-provider
    ├── TTS: TelnyxTTS (WebSocket backend) or WorkersAITTS
    └── tools: book_appointment, qualify_lead, transfer_to_owner, send_sms
    ↓
Caller's audio response
```

## Real-Time Requirements

1. **Telephony WebSocket integration** — Need a provider that connects PSTN calls directly to a WebSocket endpoint. Telnyx and Twilio can do this but it requires a media server or specific voice API config.
2. **Trick-call handling** — Spam, robocalls, wrong numbers. Need a classification step.
3. **Custom voice personality** — ElevenLabs lets customers clone their own voice from 10 min of audio. That's a Pro+ feature.
4. **Outbound calling** — One-way only at launch. Outbound (callback to owner on urgent issue) needs queue + telephony credit.
5. ** PCI compliance** — Taking payments over the phone? That changes architecture.
6. **Multi-language** — Spanish speakers in DFW. STT + LLM would need Spanish capability.

---

## Immediate Next Steps

1. **Claim `voiceline.app` domain** via Agent-as-Customer protocol or manual
2. **Set up Cloudflare account** with Workers Paid plan ($5/mo)
3. **Clone `cloudflare/agents-starter`** and build the `VoicelineReceptionist` DO
4. **Wire in telephony** — Telnyx account + DID + WebSocket test call
5. **Set up D1 for customer metadata** (accounts, billing, plan)
6. **Deploy a working proto** — single customer, real call flow
7. **Connect waitlist form** → Stripe Checkout → customer provisioning

---

## Key Links

- [CF Voice Agent Guide](https://developers.cloudflare.com/agents/guides/build-a-voice-agent/)
- [CF Voice Agents API Ref](https://developers.cloudflare.com/agents/api-reference/voice/)
- [CF Voice Agent GitHub Example](https://github.com/cloudflare/agents/tree/main/examples/voice-agent)
- [CF Workers AI Pricing](https://developers.cloudflare.com/workers-ai/platform/pricing/)
- [CF Durable Objects Pricing](https://developers.cloudflare.com/durable-objects/platform/pricing/)
- [CF Workers Pricing](https://developers.cloudflare.com/workers/platform/pricing/)
- [Agents SDK](https://developers.cloudflare.com/agent-setup/)
- [`@cloudflare/voice` npm](https://www.npmjs.com/package/@cloudflare/voice)
- [workers-ai-provider (AI SDK)](https://www.npmjs.com/package/workers-ai-provider)

---

## Complete Cost Model by Tier

### Starter ($79/mo) — 500 min/month

| Cost | Per Customer | 50 Customers |
|------|-------------|-------------|
| AI inference | ~$0.14 | $7.00 |
| DO compute | ~$0.00 | $0.00 |
| Telnyx minutes | 500 × $0.004 | $2.00 |
| D1 meta writes | ~$0.01 | $0.50 |
| **Total infra** | **~$2.15** | **~$107.50** |
| **Margin** | **97.3%** | **97.3%** |

### Pro ($149/mo) — 2,000 min/month

| Cost | Per Customer | 30 Customers |
|------|-------------|-------------|
| AI inference | ~$0.55 | $16.50 |
| DO compute | ~$0.00 | $0.00 |
| Telnyx minutes | 2,000 × $0.004 | $8.00 |
| D1 meta writes | ~$0.04 | $1.20 |
| **Total infra** | **~$8.59** | **~$257.70** |
| **Margin** | **94.2%** | **94.2%** |

### Business ($279/mo) — unlimited

| Cost | Per Customer | 20 Customers |
|------|-------------|-------------|
| AI inference | ~$2.00 | $40.00 |
| DO compute | ~$0.00 | $0.00 |
| Telnyx minutes | 5,000 × $0.004 (est) | $20.00 |
| D1 meta writes | ~$0.10 | $2.00 |
| **Total infra** | **~$22.10** | **~$442.00** |
| **Margin** | **92.1%** | **92.1%** |

**Key insight:** Infrastructure cost per customer is under $25/mo even at the top tier. The margin story is exceptional at all price points.
