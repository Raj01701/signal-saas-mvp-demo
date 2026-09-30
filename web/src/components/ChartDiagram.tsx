import { type ChartStyle, chartCells, labelsBySign, type Placement } from "@/lib/chart-layout";

const SIGN_SHORT = ["Ar", "Ta", "Ge", "Cn", "Le", "Vi", "Li", "Sc", "Sg", "Cp", "Aq", "Pi"];

interface Props {
  style: ChartStyle;
  ascendantSign: number;
  placements: Placement[];
  title: string;
}

/** A D1 or divisional chart in the North, South or East Indian style (SVG). */
export function ChartDiagram({ style, ascendantSign, placements, title }: Props) {
  const cells = chartCells(style, ascendantSign);
  const labels = labelsBySign(placements);
  const summary = cells
    .filter((c) => labels.has(c.sign))
    .map((c) => `house ${c.house}: ${labels.get(c.sign)?.join(", ")}`)
    .join("; ");
  return (
    <figure className="w-full max-w-sm">
      <svg
        viewBox="-1 -1 102 102"
        role="img"
        aria-label={`${title}, ${style} Indian style. ${summary}`}
        className="h-auto w-full text-zinc-800 dark:text-zinc-100"
      >
        <rect x="0" y="0" width="100" height="100" fill="none" stroke="currentColor" strokeWidth="0.6" />
        {cells.map((cell) => {
          const [x, y] = cell.anchor;
          const planets = labels.get(cell.sign) ?? [];
          const isLagna = cell.house === 1;
          return (
            <g key={cell.sign}>
              <polygon
                points={cell.points.map((p) => p.join(",")).join(" ")}
                fill={isLagna ? "rgb(245 158 11 / 0.12)" : "none"}
                stroke="currentColor"
                strokeWidth="0.4"
              />
              <text x={x} y={y - 3.5 - (planets.length - 1) * 2} textAnchor="middle" fontSize="3" opacity="0.6">
                {style === "north" ? cell.sign + 1 : SIGN_SHORT[cell.sign]}
                {isLagna && style !== "north" ? " Asc" : ""}
              </text>
              {planets.map((label, i) => (
                <text
                  key={label}
                  x={x}
                  y={y + 1 + (i - (planets.length - 1) / 2) * 4}
                  textAnchor="middle"
                  fontSize="3.6"
                  fontWeight="600"
                >
                  {label}
                </text>
              ))}
            </g>
          );
        })}
      </svg>
      <figcaption className="mt-1 text-center text-sm text-zinc-600 dark:text-zinc-400">{title}</figcaption>
    </figure>
  );
}
