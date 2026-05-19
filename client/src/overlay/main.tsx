import { createRoot } from "react-dom/client";

function Overlay() {
  return (
    <div
      style={{
        background: "rgba(0,0,0,0.7)",
        color: "#fff",
        padding: 12,
        borderRadius: 8,
        fontFamily: "system-ui",
        fontSize: 14,
      }}
    >
      <strong>LOL Helper Overlay</strong>
      <div style={{ marginTop: 6, fontSize: 12, opacity: 0.7 }}>
        Augment/item recommendations show here when a Riot client event fires.
      </div>
    </div>
  );
}

const root = document.getElementById("root");
if (!root) throw new Error("missing #root");
createRoot(root).render(<Overlay />);
