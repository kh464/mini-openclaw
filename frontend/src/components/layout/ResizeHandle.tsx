"use client";

import { useCallback, useRef } from "react";

interface Props {
  onResize: (delta: number) => void;
  direction?: "horizontal" | "vertical";
}

export default function ResizeHandle({ onResize, direction = "horizontal" }: Props) {
  const isDragging = useRef(false);
  const lastPos = useRef(0);

  const handleMouseDown = useCallback(
    (e: React.MouseEvent) => {
      isDragging.current = true;
      lastPos.current = direction === "horizontal" ? e.clientX : e.clientY;

      const handleMouseMove = (e: MouseEvent) => {
        if (!isDragging.current) return;
        const pos = direction === "horizontal" ? e.clientX : e.clientY;
        const delta = pos - lastPos.current;
        lastPos.current = pos;
        onResize(delta);
      };

      const handleMouseUp = () => {
        isDragging.current = false;
        document.removeEventListener("mousemove", handleMouseMove);
        document.removeEventListener("mouseup", handleMouseUp);
        document.body.style.cursor = "";
        document.body.style.userSelect = "";
      };

      document.addEventListener("mousemove", handleMouseMove);
      document.addEventListener("mouseup", handleMouseUp);
      document.body.style.cursor = direction === "horizontal" ? "col-resize" : "row-resize";
      document.body.style.userSelect = "none";
    },
    [onResize, direction]
  );

  return (
    <div
      onMouseDown={handleMouseDown}
      className={`${
        direction === "horizontal" ? "w-1 cursor-col-resize hover:bg-blue-300" : "h-1 cursor-row-resize hover:bg-blue-300"
      } bg-gray-200/50 transition-colors flex-shrink-0`}
    />
  );
}
