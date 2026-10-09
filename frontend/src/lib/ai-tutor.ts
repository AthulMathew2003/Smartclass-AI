import { apiFetch } from "./api";

export interface AiTutorSourceItem {
  material_id: string;
  title: string;
  filename: string;
  page_number?: number | null;
  slide_number?: number | null;
}

export interface AiTutorMessage {
  message_id: string;
  conversation_id: string;
  role: "user" | "assistant";
  content: string;
  sources?: AiTutorSourceItem[] | null;
  created_at: string;
}

export interface AiTutorConversation {
  conversation_id: string;
  subject_id: string;
  title: string;
  created_at: string;
  updated_at: string;
  message_count: number;
}

export interface AiTutorConversationDetail extends AiTutorConversation {
  messages: AiTutorMessage[];
}

export interface AiTutorSendMessageResponse {
  user_message: AiTutorMessage;
  assistant_message: AiTutorMessage;
}

// ── API Methods ──────────────────────────────────────────────────

export async function fetchAiTutorConversations(
  subjectId: string
): Promise<AiTutorConversation[]> {
  return await apiFetch<AiTutorConversation[]>(
    `/ai-tutor/subjects/${encodeURIComponent(subjectId)}/conversations`
  );
}

export async function createAiTutorConversation(
  subjectId: string,
  title?: string
): Promise<AiTutorConversation> {
  return await apiFetch<AiTutorConversation>(
    `/ai-tutor/subjects/${encodeURIComponent(subjectId)}/conversations`,
    {
      method: "POST",
      body: JSON.stringify({ title: title || undefined }),
    }
  );
}

export async function fetchAiTutorConversation(
  subjectId: string,
  conversationId: string
): Promise<AiTutorConversationDetail> {
  return await apiFetch<AiTutorConversationDetail>(
    `/ai-tutor/subjects/${encodeURIComponent(subjectId)}/conversations/${encodeURIComponent(conversationId)}`
  );
}

export async function deleteAiTutorConversation(
  subjectId: string,
  conversationId: string
): Promise<{ message: string }> {
  return await apiFetch<{ message: string }>(
    `/ai-tutor/subjects/${encodeURIComponent(subjectId)}/conversations/${encodeURIComponent(conversationId)}`,
    {
      method: "DELETE",
    }
  );
}

export async function sendAiTutorMessage(
  subjectId: string,
  conversationId: string,
  content: string
): Promise<AiTutorSendMessageResponse> {
  return await apiFetch<AiTutorSendMessageResponse>(
    `/ai-tutor/subjects/${encodeURIComponent(subjectId)}/conversations/${encodeURIComponent(conversationId)}/messages`,
    {
      method: "POST",
      body: JSON.stringify({ content }),
    }
  );
}
