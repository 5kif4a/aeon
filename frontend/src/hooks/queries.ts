import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "../lib/api";
import type { DiaryEntry, Goal, Profile, ProfileUpdate } from "../lib/types";

export function useProfile() {
  return useQuery({ queryKey: ["profile"], queryFn: api.getProfile });
}

export function useUpdateProfile() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: ProfileUpdate) => api.updateProfile(payload),
    onSuccess: (profile: Profile) => queryClient.setQueryData(["profile"], profile),
  });
}

export function useGoal() {
  return useQuery({ queryKey: ["goal"], queryFn: api.getGoal });
}

export function useSetGoal() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (text: string) => api.setGoal(text),
    onSuccess: (goal: Goal) => queryClient.setQueryData(["goal"], goal),
  });
}

export function useCloseGoal() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: api.closeGoal,
    onSuccess: () => queryClient.setQueryData(["goal"], null),
  });
}

export function useDiary() {
  return useQuery({ queryKey: ["diary"], queryFn: api.getDiary });
}

export function useAddDiaryEntry() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (text: string) => api.addDiaryEntry(text),
    onSuccess: (entry: DiaryEntry) =>
      queryClient.setQueryData(["diary"], (entries: DiaryEntry[] | undefined) =>
        [entry, ...(entries ?? [])].slice(0, 30),
      ),
  });
}

export function useDeleteDiaryEntry() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.deleteDiaryEntry(id),
    onMutate: async (id: string) => {
      await queryClient.cancelQueries({ queryKey: ["diary"] });
      const previous = queryClient.getQueryData<DiaryEntry[]>(["diary"]);
      queryClient.setQueryData(["diary"], (entries: DiaryEntry[] | undefined) =>
        (entries ?? []).filter((entry) => entry.id !== id),
      );
      return { previous };
    },
    onError: (_error, _id, context) => {
      if (context?.previous) queryClient.setQueryData(["diary"], context.previous);
    },
  });
}

export function useStartDialog() {
  return useMutation({
    mutationFn: ({ agentId, message = "" }: { agentId: string; message?: string }) =>
      api.startDialog(agentId, message),
  });
}
