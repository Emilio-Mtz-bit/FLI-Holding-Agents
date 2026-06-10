import { create } from 'zustand';
import type { AnalysisResult, ScenarioCard, JobStatus } from '@/types/analysis';

interface AnalysisStore {
  jobId: string | null;
  status: JobStatus;
  result: AnalysisResult | null;
  errorMessage: string | null;
  scenarios: ScenarioCard[];
  breakEvenTarget: number;

  setJob: (jobId: string) => void;
  setStatus: (status: JobStatus) => void;
  setResult: (result: AnalysisResult) => void;
  setError: (msg: string) => void;
  setScenarios: (cards: ScenarioCard[]) => void;
  updateScenario: (id: string, patch: Partial<ScenarioCard>) => void;
  addScenario: (card: ScenarioCard) => void;
  removeScenario: (id: string) => void;
  setBreakEvenTarget: (val: number) => void;
  reset: () => void;
}

export const useAnalysisStore = create<AnalysisStore>((set) => ({
  jobId: null,
  status: 'idle',
  result: null,
  errorMessage: null,
  scenarios: [],
  breakEvenTarget: 1_500_000,

  setJob: (jobId) => set({ jobId, status: 'pending' }),
  setStatus: (status) => set({ status }),
  setResult: (result) => set({ result, status: 'done' }),
  setError: (errorMessage) => set({ errorMessage, status: 'error' }),
  setScenarios: (scenarios) => set({ scenarios }),
  updateScenario: (id, patch) =>
    set((s) => ({
      scenarios: s.scenarios.map((c) => (c.id === id ? { ...c, ...patch } : c)),
    })),
  addScenario: (card) => set((s) => ({ scenarios: [...s.scenarios, card] })),
  removeScenario: (id) =>
    set((s) => ({ scenarios: s.scenarios.filter((c) => c.id !== id) })),
  setBreakEvenTarget: (breakEvenTarget) => set({ breakEvenTarget }),
  reset: () =>
    set({ jobId: null, status: 'idle', result: null, errorMessage: null, scenarios: [] }),
}));
