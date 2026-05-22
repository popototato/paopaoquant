import { motion } from "framer-motion";
import type { AiInsight } from "./types";

const DOT: Record<AiInsight["severity"], string> = {
  info: "bg-liq-accent",
  warn: "bg-amber-400",
  critical: "bg-liq-short",
};

type Props = {
  insights: AiInsight[];
};

export default function AiInsightPanel({ insights }: Props) {
  return (
    <ul className="space-y-2">
      {insights.map((insight, i) => (
        <motion.li
          key={insight.id}
          initial={{ opacity: 0, x: -6 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: i * 0.06 }}
          className="flex gap-2 text-[11px] leading-snug text-liq-text/90"
        >
          <span
            className={`mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full ${DOT[insight.severity]}`}
            style={{
              boxShadow:
                insight.severity === "critical"
                  ? "0 0 6px rgba(239,68,68,0.6)"
                  : undefined,
            }}
          />
          <span>{insight.text}</span>
        </motion.li>
      ))}
    </ul>
  );
}
