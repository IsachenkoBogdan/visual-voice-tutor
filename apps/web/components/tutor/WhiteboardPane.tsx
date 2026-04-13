"use client";

import { useEffect, useRef } from "react";
import dynamic from "next/dynamic";
import { Editor } from "tldraw";

import { PlannedBoardAction } from "@/lib/contracts";
import { applyBoardAction } from "@/lib/board-actions";

const TldrawCanvas = dynamic(() => import("tldraw").then((mod) => mod.Tldraw), {
  ssr: false,
  loading: () => <div className="flex h-full items-center justify-center text-sm text-zinc-500">Loading whiteboard...</div>,
});

interface WhiteboardPaneProps {
  actions: PlannedBoardAction[];
  onActionApplied?: (actionId: string) => void;
  onEditorReady?: (editor: Editor) => void;
}

export function WhiteboardPane({ actions, onActionApplied, onEditorReady }: WhiteboardPaneProps) {
  const editorRef = useRef<Editor | null>(null);
  const appliedActionIdsRef = useRef<Set<string>>(new Set());

  useEffect(() => {
    if (actions.length === 0) {
      appliedActionIdsRef.current.clear();
      return;
    }

    const editor = editorRef.current;
    if (!editor) {
      return;
    }

    for (const action of actions) {
      if (appliedActionIdsRef.current.has(action.action_id)) {
        continue;
      }

      applyBoardAction(editor, action);
      appliedActionIdsRef.current.add(action.action_id);
      onActionApplied?.(action.action_id);
    }
  }, [actions, onActionApplied]);

  return (
    <section className="h-full overflow-hidden rounded-xl border border-zinc-200 bg-white shadow-sm">
      <TldrawCanvas
        onMount={(editor) => {
          editorRef.current = editor;
          onEditorReady?.(editor);
        }}
      />
    </section>
  );
}
