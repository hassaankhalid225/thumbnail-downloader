"use client";

import { motion, useMotionValue, useSpring, useTransform } from "framer-motion";
import { useEffect, useState } from "react";

import { useReducedMotion } from "@/components/ui";
import { scoreColor, scoreLabel } from "@/lib/colors";

/**
 * The headline gauge. An arc rather than a full ring: a full circle reads as a progress
 * spinner, an open arc reads as a dial on an instrument, which is what this is.
 */
export function ScoreDial({
  score,
  size = 190,
  label = "ThumbIQ Score",
}: {
  score: number | null;
  size?: number;
  label?: string;
}) {
  const reduced = useReducedMotion();
  const [display, setDisplay] = useState(0);

  const stroke = size * 0.075;
  const radius = (size - stroke) / 2;
  const sweep = 260; // degrees of arc
  const circumference = 2 * Math.PI * radius;
  const arcLength = (sweep / 360) * circumference;

  const progress = useMotionValue(0);
  const spring = useSpring(progress, { stiffness: 60, damping: 16, mass: 0.9 });
  const dashOffset = useTransform(spring, (value) => arcLength * (1 - value));

  useEffect(() => {
    const target = (score ?? 0) / 100;
    if (reduced) {
      progress.set(target);
      setDisplay(score ?? 0);
      return;
    }
    progress.set(0);
    const animation = spring.on("change", (value) => setDisplay(Math.round(value * 100)));
    progress.set(target);
    return animation;
  }, [score, progress, spring, reduced]);

  const color = scoreColor(score);

  return (
    <div
      className="relative flex shrink-0 items-center justify-center"
      style={{ width: size, height: size }}
      role="img"
      aria-label={`${label}: ${score ?? "not measured"} out of 100`}
    >
      <svg
        width={size}
        height={size}
        viewBox={`0 0 ${size} ${size}`}
        // Rotate so the arc gap sits at the bottom, like a real gauge.
        style={{ transform: `rotate(${90 + (360 - sweep) / 2}deg)` }}
        aria-hidden="true"
      >
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="#232330"
          strokeWidth={stroke}
          strokeLinecap="round"
          strokeDasharray={`${arcLength} ${circumference}`}
        />
        <motion.circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke={color}
          strokeWidth={stroke}
          strokeLinecap="round"
          strokeDasharray={`${arcLength} ${circumference}`}
          style={{ strokeDashoffset: dashOffset, filter: `drop-shadow(0 0 10px ${color}55)` }}
        />
      </svg>

      {/* Everything inside scales with `size` and sits slightly above centre — the arc
          gap is at the bottom, so centred content collides with the stroke on the
          smaller dials used in compare mode. */}
      <div
        className="absolute inset-0 flex flex-col items-center justify-center"
        style={{ transform: `translateY(${-size * 0.045}px)` }}
      >
        <span
          className="mono font-black leading-none"
          style={{ color, fontSize: size * 0.27 }}
        >
          {score === null ? "—" : display}
        </span>
        <span
          className="eyebrow"
          style={{ fontSize: Math.max(8, size * 0.058), marginTop: size * 0.05 }}
        >
          {scoreLabel(score)}
        </span>
      </div>
    </div>
  );
}
