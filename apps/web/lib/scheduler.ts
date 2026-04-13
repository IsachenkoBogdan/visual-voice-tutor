import { AnchorTiming, PlannedBoardAction } from "@/lib/contracts";

interface QueuedAction {
  action: PlannedBoardAction;
  dispatch: (action: PlannedBoardAction) => void;
}

export interface SchedulerSnapshot {
  turnId: string | null;
  anchorCount: number;
  pendingActions: number;
  queuedBeforePlayback: number;
  pendingActionIds: string[];
  timelineStartedAt: number | null;
  durationMs: number | null;
  playbackStarted: boolean;
  interrupted: boolean;
}

export class PlaybackScheduler {
  private turnId: string | null = null;
  private anchorMap = new Map<string, number>();
  private pendingTimers = new Map<string, number>();
  private queuedActions = new Map<string, QueuedAction>();
  private timelineStartedAt: number | null = null;
  private durationMs: number | null = null;
  private playbackStarted = false;
  private interrupted = false;

  beginTurn(turnId: string, durationMs: number, anchors: AnchorTiming[]): void {
    this.clear();
    this.turnId = turnId;
    this.durationMs = durationMs;
    this.playbackStarted = false;
    this.interrupted = false;
    this.registerAnchors(anchors);
  }

  registerAnchors(anchors: AnchorTiming[]): void {
    for (const anchor of anchors) {
      this.anchorMap.set(anchor.anchor_id, anchor.time_ms);
    }
  }

  markPlaybackStarted(turnId: string): void {
    if (this.turnId !== turnId || this.interrupted || this.playbackStarted) {
      return;
    }

    this.playbackStarted = true;
    this.timelineStartedAt = performance.now();

    for (const queued of this.queuedActions.values()) {
      this.armTimer(queued.action, queued.dispatch);
    }
    this.queuedActions.clear();
  }

  scheduleAction(action: PlannedBoardAction, dispatch: (action: PlannedBoardAction) => void): void {
    if (this.interrupted) {
      return;
    }

    if (!this.playbackStarted) {
      this.queuedActions.set(action.action_id, { action, dispatch });
      return;
    }

    this.armTimer(action, dispatch);
  }

  cancelPendingActions(): void {
    for (const timerId of this.pendingTimers.values()) {
      window.clearTimeout(timerId);
    }
    this.pendingTimers.clear();
    this.queuedActions.clear();
  }

  interrupt(turnId: string): void {
    if (this.turnId !== turnId) {
      return;
    }
    this.interrupted = true;
    this.cancelPendingActions();
  }

  clear(): void {
    this.cancelPendingActions();
    this.anchorMap.clear();
    this.turnId = null;
    this.timelineStartedAt = null;
    this.durationMs = null;
    this.playbackStarted = false;
    this.interrupted = false;
  }

  getSnapshot(): SchedulerSnapshot {
    return {
      turnId: this.turnId,
      anchorCount: this.anchorMap.size,
      pendingActions: this.pendingTimers.size,
      queuedBeforePlayback: this.queuedActions.size,
      pendingActionIds: [
        ...Array.from(this.pendingTimers.keys()),
        ...Array.from(this.queuedActions.keys()),
      ],
      timelineStartedAt: this.timelineStartedAt,
      durationMs: this.durationMs,
      playbackStarted: this.playbackStarted,
      interrupted: this.interrupted,
    };
  }

  private armTimer(action: PlannedBoardAction, dispatch: (action: PlannedBoardAction) => void): void {
    const targetMs = this.resolveActionTime(action);
    const elapsedMs = this.timelineStartedAt === null ? 0 : performance.now() - this.timelineStartedAt;
    const delayMs = Math.max(0, targetMs - elapsedMs);

    const timerId = window.setTimeout(() => {
      this.pendingTimers.delete(action.action_id);
      if (this.interrupted) {
        return;
      }
      dispatch(action);
    }, delayMs);

    this.pendingTimers.set(action.action_id, timerId);
  }

  private resolveActionTime(action: PlannedBoardAction): number {
    switch (action.schedule.mode) {
      case "at_start":
        return 0;
      case "at_end":
        return this.durationMs ?? 0;
      case "anchor": {
        const anchorBase = this.anchorMap.get(action.schedule.anchor_id) ?? 0;
        return Math.max(0, anchorBase + action.schedule.offset_ms);
      }
      default:
        return 0;
    }
  }
}
