import { CheckStepPayload, ConnectionState, StreamEvent, parseStreamEvent } from "@/lib/contracts";

export interface TutorWsClientHandlers {
  onConnectionStateChange?: (state: ConnectionState) => void;
  onEvent?: (event: StreamEvent) => void;
  onRawMessage?: (message: string) => void;
  onError?: (error: string) => void;
}

export class TutorWsClient {
  private socket: WebSocket | null = null;
  private readonly url: string;
  private readonly handlers: TutorWsClientHandlers;

  constructor(url: string, handlers: TutorWsClientHandlers = {}) {
    this.url = url;
    this.handlers = handlers;
  }

  connect(): void {
    if (this.socket && this.socket.readyState === WebSocket.OPEN) {
      return;
    }

    this.handlers.onConnectionStateChange?.("connecting");
    this.socket = new WebSocket(this.url);

    this.socket.onopen = () => {
      this.handlers.onConnectionStateChange?.("connected");
    };

    this.socket.onclose = () => {
      this.handlers.onConnectionStateChange?.("disconnected");
    };

    this.socket.onerror = () => {
      this.handlers.onConnectionStateChange?.("error");
      this.handlers.onError?.("WebSocket transport error");
    };

    this.socket.onmessage = (event: MessageEvent<string>) => {
      this.handlers.onRawMessage?.(event.data);
      const parsed = parseStreamEvent(event.data);
      if (!parsed) {
        this.handlers.onError?.("Received malformed stream event");
        return;
      }
      this.handlers.onEvent?.(parsed);
    };
  }

  runMockTurn(): void {
    this.send({ type: "run_mock_turn" });
  }

  checkStep(payload: CheckStepPayload): void {
    this.send({ type: "check_step", payload });
  }

  transcribeAudio(audioB64: string, mimeType = "audio/wav"): void {
    this.send({
      type: "asr.transcribe",
      payload: {
        audio_b64: audioB64,
        mime_type: mimeType,
      },
    });
  }

  interruptTurn(turnId: string): void {
    this.send({ type: "interrupt", turn_id: turnId, reason: "student_interrupt" });
  }

  disconnect(): void {
    if (!this.socket) {
      return;
    }

    this.socket.close();
    this.socket = null;
    this.handlers.onConnectionStateChange?.("disconnected");
  }

  private send(payload: Record<string, unknown>): void {
    if (!this.socket || this.socket.readyState !== WebSocket.OPEN) {
      this.handlers.onError?.("WebSocket is not connected");
      return;
    }

    this.socket.send(JSON.stringify(payload));
  }
}
