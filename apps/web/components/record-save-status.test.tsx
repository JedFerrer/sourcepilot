import { act, cleanup, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { RecordSaveStatus } from "./record-save-status";

afterEach(() => { cleanup(); vi.useRealTimers(); });

it("stays quiet on load and after pending ends without a confirmed save", () => {
  const view = render(<RecordSaveStatus dirty={false} pending={false} />);
  expect(screen.queryByRole("status")).not.toBeInTheDocument();
  view.rerender(<RecordSaveStatus dirty={false} pending />);
  expect(screen.getByRole("status")).toHaveTextContent("Saving");
  view.rerender(<RecordSaveStatus dirty={false} pending={false} />);
  expect(screen.queryByRole("status")).not.toBeInTheDocument();
});

it("shows successful saves for three seconds and restarts for another save", () => {
  vi.useFakeTimers();
  const view = render(<RecordSaveStatus dirty={false} pending={false} savedVersion={0} />);
  view.rerender(<RecordSaveStatus dirty={false} pending={false} savedVersion={1} />);
  expect(screen.getByRole("status")).toHaveTextContent("Saved");
  act(() => vi.advanceTimersByTime(2000));
  view.rerender(<RecordSaveStatus dirty={false} pending={false} savedVersion={2} />);
  act(() => vi.advanceTimersByTime(2000));
  expect(screen.getByRole("status")).toHaveTextContent("Saved");
  act(() => vi.advanceTimersByTime(1000));
  expect(screen.queryByRole("status")).not.toBeInTheDocument();
});

it("keeps unsaved, error and conflict messages visible beyond the success timer", () => {
  vi.useFakeTimers();
  const view = render(<RecordSaveStatus dirty pending={false} savedVersion={1} />);
  act(() => vi.advanceTimersByTime(5000));
  expect(screen.getByRole("status")).toHaveTextContent("Unsaved changes");
  view.rerender(<RecordSaveStatus dirty pending={false} error="Failed" savedVersion={1} />);
  expect(screen.getByRole("status")).toHaveTextContent("Save failed");
  view.rerender(<RecordSaveStatus dirty pending={false} conflict savedVersion={1} />);
  expect(screen.getByRole("status")).toHaveTextContent("Saved elsewhere");
});
