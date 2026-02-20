import { BaseEdge, getBezierPath, EdgeProps } from '@xyflow/react';

export default function BackEdge({
  id,
  sourceX,
  sourceY,
  targetX,
  targetY,
  sourcePosition,
  targetPosition,
  style,
  markerEnd,
}: EdgeProps) {
  // We want to draw a sweeping curve that routes under the main layout to visually distinguish back-edges
  // Instead of a direct bezier, we can manually create an SVG path or adjust the control points.
  // Standard bezier is fine, but we'll add a CSS animation class.
  const [edgePath] = getBezierPath({
    sourceX,
    sourceY,
    targetX,
    targetY,
    sourcePosition,
    targetPosition,
  });

  return (
    <>
      <BaseEdge path={edgePath} markerEnd={markerEnd} style={style} id={id} />
      {/* Invisible edge for interaction */}
      <path
        d={edgePath}
        fill="none"
        strokeOpacity={0}
        strokeWidth={20}
        className="react-flow__edge-interaction"
      />
    </>
  );
}
