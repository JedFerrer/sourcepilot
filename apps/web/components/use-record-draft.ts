"use client";
import { useCallback, useEffect, useReducer, useRef, useState } from "react";
import { createDraft, reduceDraft, sameRecord, type DraftAction } from "../lib/record-draft";

export function useRecordDraft<T>(remote: T) {
  const [state, rawDispatch] = useReducer(reduceDraft<T>, remote, createDraft<T>);
  const [savedVersion, setSavedVersion] = useState(0);
  const dispatch = useCallback((action: DraftAction<T>) => {
    rawDispatch(action);
    if (action.type === "saved") setSavedVersion((version) => version + 1);
  }, []);
  const latest = useRef(state);
  latest.current = state;
  useEffect(() => { dispatch({ type: "receive", value: remote }); }, [remote, dispatch]);
  const edit = useCallback((value: T | ((current: T) => T)) => {
    const next = typeof value === "function" ? (value as (current: T) => T)(latest.current.draft) : value;
    latest.current = reduceDraft(latest.current, { type: "edit", value: next });
    dispatch({ type: "edit", value: next });
  }, [dispatch]);
  const begin = useCallback((value?: T) => {
    const current = latest.current;
    if (current.submitted !== null || current.conflict || current.uncertain) return null;
    latest.current = reduceDraft<T>(current, { type: "submit", value });
    dispatch({ type: "submit", value });
    return value === undefined ? current.draft : value;
  }, [dispatch]);
  return { savedVersion, state, edit, begin, dispatch, dirty: !sameRecord(state.draft, state.baseline), pending: state.submitted !== null };
}
