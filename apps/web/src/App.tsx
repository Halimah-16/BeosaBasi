import React from "react";
import { healthLabel } from "./health";

export default function App(): React.JSX.Element {
  return (
    <main>
      <h1>BeosaBasi</h1>
      <p>{healthLabel()} (scaffold TK-000; app nyata di TK-040+)</p>
    </main>
  );
}
