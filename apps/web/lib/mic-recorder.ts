export type MicState = "idle" | "recording" | "processing" | "unsupported" | "error";

export class MicRecorder {
  private mediaRecorder: MediaRecorder | null = null;
  private chunks: BlobPart[] = [];
  private state: MicState = "idle";

  getState(): MicState {
    return this.state;
  }

  async start(): Promise<boolean> {
    if (!isMediaRecorderSupported()) {
      this.state = "unsupported";
      return false;
    }

    if (this.mediaRecorder && this.mediaRecorder.state === "recording") {
      return true;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      this.chunks = [];
      const mimeType = pickMimeType();
      this.mediaRecorder = new MediaRecorder(stream, mimeType ? { mimeType } : undefined);
      this.mediaRecorder.ondataavailable = (event: BlobEvent) => {
        if (event.data.size > 0) {
          this.chunks.push(event.data);
        }
      };
      this.mediaRecorder.start();
      this.state = "recording";
      return true;
    } catch {
      this.state = "error";
      return false;
    }
  }

  async stopAndCollect(): Promise<{ blob: Blob; mimeType: string } | null> {
    const recorder = this.mediaRecorder;
    if (!recorder || recorder.state !== "recording") {
      return null;
    }

    this.state = "processing";

    const stopped = new Promise<{ blob: Blob; mimeType: string }>((resolve) => {
      recorder.onstop = () => {
        const mimeType = recorder.mimeType || "audio/webm";
        const blob = new Blob(this.chunks, { type: mimeType });
        for (const track of recorder.stream.getTracks()) {
          track.stop();
        }
        this.mediaRecorder = null;
        this.chunks = [];
        this.state = "idle";
        resolve({ blob, mimeType });
      };
    });

    recorder.stop();
    return stopped;
  }
}

function isMediaRecorderSupported(): boolean {
  return typeof window !== "undefined" && typeof navigator !== "undefined" && "MediaRecorder" in window;
}

function pickMimeType(): string | undefined {
  const candidates = ["audio/webm;codecs=opus", "audio/webm", "audio/ogg;codecs=opus"];
  for (const candidate of candidates) {
    if (MediaRecorder.isTypeSupported(candidate)) {
      return candidate;
    }
  }
  return undefined;
}
