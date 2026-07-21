/**
 * Patient avatar — a soft, deterministically-coloured initials circle.
 * The hue is derived from the name so each patient keeps a stable colour,
 * staying within calm pastel tones that fit the healthcare palette.
 */

function initials(name: string): string {
  const parts = name.trim().split(/\s+/);
  const first = parts[0]?.[0] ?? "";
  const second = parts.length > 1 ? (parts[parts.length - 1]?.[0] ?? "") : "";
  return (first + second).toUpperCase();
}

function hue(name: string): number {
  let h = 0;
  for (const ch of name) h = (h * 31 + ch.charCodeAt(0)) % 360;
  return h;
}

export default function Avatar({
  name,
  size = 40,
}: {
  name: string;
  size?: number;
}) {
  const h = hue(name);
  return (
    <span
      aria-hidden
      className="flex shrink-0 items-center justify-center rounded-full font-bold uppercase"
      style={{
        width: size,
        height: size,
        fontSize: size * 0.38,
        backgroundColor: `hsl(${h} 42% 90%)`,
        color: `hsl(${h} 45% 30%)`,
      }}
    >
      {initials(name)}
    </span>
  );
}
