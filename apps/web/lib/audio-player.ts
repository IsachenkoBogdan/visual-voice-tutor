import { AudioPlaybackState, UtteranceAudioChunkEvent, UtteranceAudioEndEvent } from "@/lib/contracts";

interface AudioChunkBuffer {
  utteranceId: string;
  encoding: string;
  sampleRateHz: number;
  channels: number;
  chunks: Map<number, Uint8Array>;
  ended: boolean;
  expectedTotalChunks: number | null;
  totalBytes: number | null;
}

export interface AudioPlayerSnapshot {
  state: AudioPlaybackState;
  activeUtteranceId: string | null;
  bufferedChunks: number;
  bufferedBytes: number;
  expectedChunks: number | null;
}

export interface AudioPlayerCallbacks {
  onStateChange?: (state: AudioPlaybackState) => void;
  onPlaybackStarted?: (utteranceId: string) => void;
  onPlaybackEnded?: (utteranceId: string) => void;
  onError?: (message: string) => void;
}

export class AudioPlayer {
  private audioContext: AudioContext | null = null;
  private currentSource: AudioBufferSourceNode | null = null;
  private buffers = new Map<string, AudioChunkBuffer>();
  private activeUtteranceId: string | null = null;
  private lastTouchedUtteranceId: string | null = null;
  private state: AudioPlaybackState = "idle";
  private readonly callbacks: AudioPlayerCallbacks;

  constructor(callbacks: AudioPlayerCallbacks = {}) {
    this.callbacks = callbacks;
  }

  enqueueChunk(payload: UtteranceAudioChunkEvent["payload"]): void {
    const buffer = this.ensureBuffer(
      payload.utterance_id,
      payload.encoding,
      payload.sample_rate_hz,
      payload.channels,
    );

    if (!buffer.chunks.has(payload.seq)) {
      buffer.chunks.set(payload.seq, decodeBase64(payload.chunk_b64));
    }

    if (this.state === "idle" || this.state === "ended") {
      this.setState("buffering");
    }
  }

  markEnded(payload: UtteranceAudioEndEvent["payload"]): void {
    const buffer = this.ensureBuffer(payload.utterance_id, "", 0, 0);
    buffer.ended = true;
    buffer.expectedTotalChunks = payload.total_chunks;
    buffer.totalBytes = payload.total_bytes;
  }

  async startIfBuffered(utteranceId: string): Promise<boolean> {
    const buffer = this.buffers.get(utteranceId);
    if (!buffer || !buffer.ended) {
      return false;
    }

    if (buffer.expectedTotalChunks !== null && buffer.chunks.size < buffer.expectedTotalChunks) {
      return false;
    }

    const audioContext = this.ensureAudioContext();
    const merged = mergeChunks(buffer.chunks);

    try {
      const audioData = new Uint8Array(merged.byteLength);
      audioData.set(merged);
      const decoded = await audioContext.decodeAudioData(audioData.buffer);
      if (this.currentSource) {
        this.currentSource.stop();
        this.currentSource.disconnect();
      }

      const source = audioContext.createBufferSource();
      source.buffer = decoded;
      source.connect(audioContext.destination);
      source.onended = () => {
        this.setState("ended");
        this.callbacks.onPlaybackEnded?.(utteranceId);
      };

      await audioContext.resume();
      source.start(0);

      this.currentSource = source;
      this.activeUtteranceId = utteranceId;
      this.lastTouchedUtteranceId = utteranceId;
      this.setState("playing");
      this.callbacks.onPlaybackStarted?.(utteranceId);
      return true;
    } catch (error) {
      this.setState("error");
      this.callbacks.onError?.(`Audio decode/playback failed: ${String(error)}`);
      return false;
    }
  }

  setFallbackState(): void {
    this.setState("fallback");
  }

  stopAndClear(): void {
    if (this.currentSource) {
      try {
        this.currentSource.stop(0);
      } catch {
        // no-op
      }
      this.currentSource.disconnect();
      this.currentSource = null;
    }

    this.buffers.clear();
    this.activeUtteranceId = null;
    this.lastTouchedUtteranceId = null;
    this.setState("idle");
  }

  getSnapshot(): AudioPlayerSnapshot {
    const currentUtteranceId = this.activeUtteranceId ?? this.lastTouchedUtteranceId;
    const activeBuffer = currentUtteranceId ? this.buffers.get(currentUtteranceId) : null;
    return {
      state: this.state,
      activeUtteranceId: currentUtteranceId,
      bufferedChunks: activeBuffer?.chunks.size ?? 0,
      bufferedBytes: activeBuffer ? totalChunkBytes(activeBuffer.chunks) : 0,
      expectedChunks: activeBuffer?.expectedTotalChunks ?? null,
    };
  }

  private ensureAudioContext(): AudioContext {
    if (!this.audioContext) {
      this.audioContext = new AudioContext();
    }
    return this.audioContext;
  }

  private ensureBuffer(
    utteranceId: string,
    encoding: string,
    sampleRateHz: number,
    channels: number,
  ): AudioChunkBuffer {
    const existing = this.buffers.get(utteranceId);
    if (existing) {
      this.lastTouchedUtteranceId = utteranceId;
      if (encoding) {
        existing.encoding = encoding;
      }
      if (sampleRateHz > 0) {
        existing.sampleRateHz = sampleRateHz;
      }
      if (channels > 0) {
        existing.channels = channels;
      }
      return existing;
    }

    const created: AudioChunkBuffer = {
      utteranceId,
      encoding,
      sampleRateHz,
      channels,
      chunks: new Map<number, Uint8Array>(),
      ended: false,
      expectedTotalChunks: null,
      totalBytes: null,
    };
    this.buffers.set(utteranceId, created);
    this.lastTouchedUtteranceId = utteranceId;
    return created;
  }

  private setState(next: AudioPlaybackState): void {
    this.state = next;
    this.callbacks.onStateChange?.(next);
  }
}

function decodeBase64(value: string): Uint8Array {
  const binary = atob(value);
  const output = new Uint8Array(binary.length);
  for (let idx = 0; idx < binary.length; idx += 1) {
    output[idx] = binary.charCodeAt(idx);
  }
  return output;
}

function mergeChunks(chunks: Map<number, Uint8Array>): Uint8Array {
  const sorted = Array.from(chunks.entries()).sort(([a], [b]) => a - b);
  const total = sorted.reduce((acc, [, chunk]) => acc + chunk.byteLength, 0);
  const merged = new Uint8Array(total);
  let offset = 0;
  for (const [, chunk] of sorted) {
    merged.set(chunk, offset);
    offset += chunk.byteLength;
  }
  return merged;
}

function totalChunkBytes(chunks: Map<number, Uint8Array>): number {
  let total = 0;
  for (const chunk of chunks.values()) {
    total += chunk.byteLength;
  }
  return total;
}
