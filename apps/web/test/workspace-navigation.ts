import { fireEvent, screen, within } from "@testing-library/react";
export async function viewStage(name: "Brief" | "Suppliers" | "Quotes" | "Comparison" | "Decision") {
  const nav = await screen.findByRole("navigation", { name: "Sourcing workflow stages" });
  fireEvent.click(within(nav).getByRole("link", { name }));
}
