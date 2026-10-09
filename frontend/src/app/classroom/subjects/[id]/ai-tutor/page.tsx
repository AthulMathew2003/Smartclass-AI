"use client";

import React, { useEffect, useState, useRef, useCallback } from "react";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import {
  AiTutorConversation,
  AiTutorMessage,
  AiTutorSourceItem,
  fetchAiTutorConversations,
  fetchAiTutorConversation,
  createAiTutorConversation,
  deleteAiTutorConversation,
  sendAiTutorMessage,
} from "@/lib/ai-tutor";
import { fetchSubject, Subject } from "@/lib/subjects";
import { getMaterialIcon } from "@/lib/materials";
import { usePermissions } from "@/lib/permissions";
import ForbiddenState from "../../../components/ForbiddenState";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";

export default function SubjectAiTutorPage() {
  const params = useParams();
  const id = params?.id as string;
  const searchParams = useSearchParams();
  const workspaceIdFromQuery = searchParams.get("workspace_id");
  const router = useRouter();

  const { hasPermission, isLoaded: permLoaded } = usePermissions();

  const [subject, setSubject] = useState<Subject | null>(null);
  const [conversations, setConversations] = useState<AiTutorConversation[]>([]);
  const [activeConversationId, setActiveConversationId] = useState<string | null>(null);
  const [messages, setMessages] = useState<AiTutorMessage[]>([]);
  
  const [loadingSubject, setLoadingSubject] = useState(true);
  const [loadingMessages, setLoadingMessages] = useState(false);
  const [sending, setSending] = useState(false);
  const [inputQuery, setInputQuery] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isForbidden, setIsForbidden] = useState(false);

  // Delete Thread Modal
  const [deleteModalOpen, setDeleteModalOpen] = useState(false);
  const [convToDelete, setConvToDelete] = useState<AiTutorConversation | null>(null);
  const [deleting, setDeleting] = useState(false);

  // Mobile sidebar toggle
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const messagesEndRef = useRef<HTMLDivElement | null>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, sending]);

  // Load subject and conversation threads
  const loadInitialData = useCallback(async () => {
    if (!id) return;
    setLoadingSubject(true);
    setError(null);
    setIsForbidden(false);

    try {
      const [subjData, convsData] = await Promise.all([
        fetchSubject(id, workspaceIdFromQuery || undefined),
        fetchAiTutorConversations(id),
      ]);
      setSubject(subjData);
      setConversations(convsData);

      if (convsData.length > 0) {
        setActiveConversationId(convsData[0].conversation_id);
      }
    } catch (err: any) {
      const msg = err?.message || "Failed to load AI Tutor.";
      if (
        msg.toLowerCase().includes("permission") ||
        msg.toLowerCase().includes("denied") ||
        msg.includes("403")
      ) {
        setIsForbidden(true);
      } else {
        setError(msg);
      }
    } finally {
      setLoadingSubject(false);
    }
  }, [id, workspaceIdFromQuery]);

  useEffect(() => {
    if (permLoaded && hasPermission("subject.read")) {
      loadInitialData();
    }
  }, [permLoaded, loadInitialData, hasPermission]);

  const skipNextLoadRef = useRef(false);

  // Load active conversation messages
  useEffect(() => {
    if (!activeConversationId || !id) {
      setMessages([]);
      return;
    }

    if (skipNextLoadRef.current) {
      skipNextLoadRef.current = false;
      return;
    }

    let isMounted = true;
    const loadConversationDetails = async () => {
      setLoadingMessages(true);
      try {
        const detail = await fetchAiTutorConversation(id, activeConversationId);
        if (isMounted) {
          setMessages(detail.messages || []);
        }
      } catch (err: any) {
        console.error("Failed to load conversation history:", err);
      } finally {
        if (isMounted) {
          setLoadingMessages(false);
        }
      }
    };

    loadConversationDetails();
    return () => {
      isMounted = false;
    };
  }, [id, activeConversationId]);

  // Create New Thread
  const handleNewChat = async () => {
    try {
      const newConv = await createAiTutorConversation(id, "New Chat");
      setConversations((prev) => [newConv, ...prev]);
      skipNextLoadRef.current = true;
      setActiveConversationId(newConv.conversation_id);
      setMessages([]);
      setSidebarOpen(false);
    } catch (err: any) {
      alert(err?.message || "Failed to create new conversation.");
    }
  };

  // Delete Thread Confirm
  const handleDeleteConversation = async () => {
    if (!convToDelete) return;
    setDeleting(true);
    try {
      await deleteAiTutorConversation(id, convToDelete.conversation_id);
      const remaining = conversations.filter(
        (c) => c.conversation_id !== convToDelete.conversation_id
      );
      setConversations(remaining);

      if (activeConversationId === convToDelete.conversation_id) {
        if (remaining.length > 0) {
          setActiveConversationId(remaining[0].conversation_id);
        } else {
          setActiveConversationId(null);
          setMessages([]);
        }
      }
      setDeleteModalOpen(false);
      setConvToDelete(null);
    } catch (err: any) {
      alert(err?.message || "Failed to delete conversation.");
    } finally {
      setDeleting(false);
    }
  };

  // Send Message
  const handleSendMessage = async (textToSend?: string) => {
    const query = (textToSend || inputQuery).trim();
    if (!query || sending) return;

    setInputQuery("");
    setError(null);
    setSending(true);

    try {
      let targetConvId = activeConversationId;

      // Auto-create thread if none is active
      if (!targetConvId) {
        const newConv = await createAiTutorConversation(id, query.slice(0, 50));
        setConversations((prev) => [newConv, ...prev]);
        skipNextLoadRef.current = true;
        setActiveConversationId(newConv.conversation_id);
        targetConvId = newConv.conversation_id;
      }

      // Optimistic user message addition
      const tempUserMsg: AiTutorMessage = {
        message_id: "temp-" + Date.now(),
        conversation_id: targetConvId,
        role: "user",
        content: query,
        created_at: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, tempUserMsg]);

      // Call API
      const result = await sendAiTutorMessage(id, targetConvId, query);

      // Update state with confirmed messages
      setMessages((prev) => [
        ...prev.filter((m) => m.message_id !== tempUserMsg.message_id),
        result.user_message,
        result.assistant_message,
      ]);

      // Refresh conversations list to update title / order
      const updatedConvs = await fetchAiTutorConversations(id);
      setConversations(updatedConvs);
    } catch (err: any) {
      setError(err?.message || "Failed to generate answer. Please try again.");
    } finally {
      setSending(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  if (!permLoaded || loadingSubject) {
    return (
      <div className="flex items-center justify-center min-h-[50vh]">
        <div className="flex items-center gap-3 text-sm font-semibold text-muted-foreground">
          <div className="w-6 h-6 border-2 border-t-transparent border-primary rounded-full animate-spin" />
          Initializing SmartClass AI Tutor...
        </div>
      </div>
    );
  }

  if (!hasPermission("subject.read") || isForbidden) {
    return (
      <ForbiddenState message="You do not have permission to access the AI Tutor for this subject." />
    );
  }

  if (error && !subject) {
    return (
      <div className="p-6 max-w-6xl mx-auto space-y-4">
        <div className="p-4 rounded-xl bg-destructive/10 text-destructive text-sm border border-destructive/20">
          {error || "Subject not found"}
        </div>
        <Button variant="outline" onClick={() => router.push("/classroom/subjects")}>
          &larr; Back to Subjects
        </Button>
      </div>
    );
  }

  const suggestedPrompts = [
    `Summarize the key topics covered in ${subject?.subject_name || "this subject"}.`,
    "What are the most important formulas, definitions, or core concepts in the notes?",
    "Explain the core chapters step-by-step with practical examples.",
    "Generate 3 practice review questions with answers from the course materials.",
  ];

  return (
    <div className="p-4 md:p-6 max-w-7xl mx-auto space-y-4 h-[calc(100vh-5rem)] flex flex-col">
      {/* Navigation Breadcrumbs */}
      <div className="flex items-center justify-between gap-2 shrink-0">
        <div className="flex items-center gap-2 text-xs font-semibold text-muted-foreground">
          <Link href="/classroom/subjects" className="hover:text-primary transition-colors">
            Subjects
          </Link>
          <span>/</span>
          <Link
            href={
              workspaceIdFromQuery
                ? `/classroom/subjects/${id}?workspace_id=${workspaceIdFromQuery}`
                : `/classroom/subjects/${id}`
            }
            className="hover:text-primary transition-colors"
          >
            {subject?.subject_name}
          </Link>
          <span>/</span>
          <span className="text-foreground flex items-center gap-1 font-bold">
            <span className="material-symbols-outlined text-[14px] text-primary">auto_awesome</span>
            AI Tutor
          </span>
        </div>

        {/* Mobile Sidebar Toggle Button */}
        <Button
          variant="outline"
          size="sm"
          onClick={() => setSidebarOpen(!sidebarOpen)}
          className="md:hidden h-8 text-xs gap-1.5"
        >
          <span className="material-symbols-outlined text-[16px]">forum</span>
          Chats ({conversations.length})
        </Button>
      </div>

      {/* Main Chat Layout Frame */}
      <div className="flex-1 flex gap-4 overflow-hidden rounded-2xl border border-[var(--outline-variant)] bg-[var(--surface-container-lowest)] shadow-xs">
        {/* Left Sidebar: Conversations / History */}
        <div
          className={`${
            sidebarOpen ? "flex" : "hidden"
          } md:flex flex-col w-72 shrink-0 border-r border-[var(--outline-variant)] bg-[var(--surface-container-low)] p-3 justify-between z-10 absolute md:static inset-y-0 left-0 max-w-[85vw] shadow-lg md:shadow-none`}
        >
          <div className="space-y-3 overflow-hidden flex flex-col h-full">
            <div className="flex items-center justify-between pb-1">
              <div className="flex items-center gap-2">
                <span className="material-symbols-outlined text-primary text-[20px]">
                  smart_toy
                </span>
                <span className="text-xs font-black uppercase tracking-wider text-foreground">
                  Threads
                </span>
              </div>
              <Button
                size="sm"
                variant="ghost"
                onClick={handleNewChat}
                title="Start new chat"
                className="h-7 px-2 text-xs font-bold text-primary hover:bg-primary/10 gap-1"
              >
                <span className="material-symbols-outlined text-[16px]">add</span>
                New Chat
              </Button>
            </div>

            {/* Conversation List */}
            <div className="flex-1 overflow-y-auto space-y-1 pr-1 custom-scrollbar">
              {conversations.length === 0 ? (
                <div className="p-4 text-center text-xs text-muted-foreground">
                  No previous conversations. Start asking questions below!
                </div>
              ) : (
                conversations.map((conv) => {
                  const isActive = conv.conversation_id === activeConversationId;
                  return (
                    <div
                      key={conv.conversation_id}
                      onClick={() => {
                        setActiveConversationId(conv.conversation_id);
                        setSidebarOpen(false);
                      }}
                      className={`group flex items-center justify-between p-2.5 rounded-xl text-xs font-medium cursor-pointer transition-all ${
                        isActive
                          ? "bg-primary text-white shadow-xs font-bold"
                          : "text-foreground hover:bg-[var(--surface-container-high)]"
                      }`}
                    >
                      <div className="flex items-center gap-2 truncate pr-2">
                        <span
                          className={`material-symbols-outlined text-[16px] shrink-0 ${
                            isActive ? "text-white" : "text-muted-foreground"
                          }`}
                        >
                          chat_bubble_outline
                        </span>
                        <span className="truncate" title={conv.title}>
                          {conv.title || "Untitled Conversation"}
                        </span>
                      </div>

                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          setConvToDelete(conv);
                          setDeleteModalOpen(true);
                        }}
                        title="Delete chat thread"
                        className={`opacity-0 group-hover:opacity-100 p-1 rounded-md transition-opacity shrink-0 ${
                          isActive
                            ? "hover:bg-white/20 text-white"
                            : "hover:bg-destructive/10 text-destructive"
                        }`}
                      >
                        <span className="material-symbols-outlined text-[14px]">delete</span>
                      </button>
                    </div>
                  );
                })
              )}
            </div>
          </div>

          {/* Sidebar Footer Info */}
          <div className="pt-3 border-t border-[var(--outline-variant)] text-[11px] text-muted-foreground flex items-center gap-1.5">
            <span className="material-symbols-outlined text-[14px] text-emerald-500">lock</span>
            Private to your student profile
          </div>
        </div>

        {/* Right Main Chat Panel */}
        <div className="flex-1 flex flex-col justify-between overflow-hidden bg-background">
          {/* Subject Context Header */}
          <div className="p-3.5 border-b border-[var(--outline-variant)] flex items-center justify-between bg-[var(--surface-container-low)]">
            <div className="flex items-center gap-2.5 truncate">
              <div className="w-8 h-8 rounded-lg bg-primary/10 text-primary flex items-center justify-center shrink-0">
                <span className="material-symbols-outlined text-[18px]">auto_awesome</span>
              </div>
              <div className="truncate">
                <h2 className="text-sm font-bold text-foreground truncate">
                  {subject?.subject_name} AI Tutor
                </h2>
                <p className="text-[10px] text-muted-foreground truncate">
                  Grounded in uploaded lecture notes, slides, and course documents.
                </p>
              </div>
            </div>

            <Badge
              variant="outline"
              className="bg-emerald-500/10 text-emerald-600 border-emerald-500/20 text-[10px] font-semibold shrink-0 gap-1 hidden sm:flex"
            >
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
              RAG Knowledge Base Connected
            </Badge>
          </div>

          {/* Chat Messages Stream Area */}
          <div className="flex-1 overflow-y-auto p-4 md:p-6 space-y-6 custom-scrollbar">
            {loadingMessages ? (
              <div className="flex items-center justify-center h-full">
                <div className="flex items-center gap-2 text-xs font-semibold text-muted-foreground">
                  <div className="w-4 h-4 border-2 border-t-transparent border-primary rounded-full animate-spin" />
                  Loading conversation history...
                </div>
              </div>
            ) : messages.length === 0 ? (
              /* Cold-Start Suggested Prompts State */
              <div className="flex flex-col items-center justify-center h-full max-w-lg mx-auto text-center py-6 space-y-6">
                <div className="w-16 h-16 rounded-2xl bg-primary/10 text-primary flex items-center justify-center shadow-inner">
                  <span className="material-symbols-outlined text-[36px]">auto_awesome</span>
                </div>

                <div className="space-y-1">
                  <h3 className="text-lg font-black text-foreground">
                    Ask anything about {subject?.subject_name}
                  </h3>
                  <p className="text-xs text-muted-foreground leading-relaxed">
                    I answer your questions strictly using the uploaded notes, slides, and reference
                    materials provided by your instructors.
                  </p>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 w-full text-left">
                  {suggestedPrompts.map((prompt, idx) => (
                    <button
                      key={idx}
                      onClick={() => handleSendMessage(prompt)}
                      className="p-3 rounded-xl border border-[var(--outline-variant)] bg-[var(--surface-container-lowest)] hover:border-primary/50 hover:bg-primary/5 text-xs text-foreground transition-all cursor-pointer flex flex-col justify-between gap-1 group shadow-2xs"
                    >
                      <span className="line-clamp-2 leading-relaxed font-medium">{prompt}</span>
                      <span className="material-symbols-outlined text-[14px] text-muted-foreground group-hover:text-primary self-end">
                        arrow_forward
                      </span>
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              messages.map((msg) => {
                const isUser = msg.role === "user";
                return (
                  <div
                    key={msg.message_id}
                    className={`flex items-start gap-3 ${isUser ? "flex-row-reverse" : "flex-row"}`}
                  >
                    {/* Role Avatar */}
                    <div
                      className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 text-xs font-bold ${
                        isUser
                          ? "bg-primary text-white"
                          : "bg-primary/10 text-primary border border-primary/20"
                      }`}
                    >
                      {isUser ? (
                        <span className="material-symbols-outlined text-[16px]">person</span>
                      ) : (
                        <span className="material-symbols-outlined text-[16px]">auto_awesome</span>
                      )}
                    </div>

                    {/* Message Bubble Body */}
                    <div
                      className={`max-w-[85%] md:max-w-[75%] space-y-3 ${
                        isUser ? "items-end" : "items-start"
                      }`}
                    >
                      <div
                        className={`p-4 rounded-2xl text-xs md:text-sm leading-relaxed whitespace-pre-wrap ${
                          isUser
                            ? "bg-primary text-white rounded-tr-none shadow-xs font-medium"
                            : "bg-[var(--surface-container-low)] text-foreground border border-[var(--outline-variant)] rounded-tl-none shadow-2xs"
                        }`}
                      >
                        {msg.content}
                      </div>

                      {/* Grounded Source Citations (Only on assistant messages with sources) */}
                      {!isUser && msg.sources && msg.sources.length > 0 && (
                        <div className="space-y-1.5 pt-1">
                          <div className="flex items-center gap-1.5 text-[11px] font-bold text-muted-foreground uppercase tracking-wider">
                            <span className="material-symbols-outlined text-[14px] text-primary">
                              verified
                            </span>
                            Cited Course Sources ({msg.sources.length})
                          </div>

                          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                            {msg.sources.map((src, sIdx) => {
                              const icon = getMaterialIcon(src.filename);
                              const locationParts = [];
                              if (src.page_number !== null && src.page_number !== undefined) {
                                locationParts.push(`Page ${src.page_number}`);
                              }
                              if (src.slide_number !== null && src.slide_number !== undefined) {
                                locationParts.push(`Slide ${src.slide_number}`);
                              }

                              return (
                                <div
                                  key={sIdx}
                                  className="p-2.5 rounded-xl border border-[var(--outline-variant)] bg-[var(--surface-container-lowest)] flex items-center gap-2.5 shadow-2xs hover:border-primary/40 transition-colors"
                                >
                                  <div className="w-7 h-7 rounded-lg bg-primary/10 text-primary flex items-center justify-center shrink-0">
                                    <span className="material-symbols-outlined text-[16px]">
                                      {icon}
                                    </span>
                                  </div>
                                  <div className="truncate flex-1">
                                    <p
                                      className="text-xs font-bold text-foreground truncate"
                                      title={src.title}
                                    >
                                      {src.title}
                                    </p>
                                    <p className="text-[10px] text-muted-foreground font-mono truncate">
                                      {src.filename}
                                    </p>
                                  </div>

                                  {locationParts.length > 0 && (
                                    <Badge
                                      variant="outline"
                                      className="text-[9px] font-bold uppercase bg-muted/40 shrink-0"
                                    >
                                      {locationParts.join(" • ")}
                                    </Badge>
                                  )}
                                </div>
                              );
                            })}
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                );
              })
            )}

            {/* In-Flight Thinking Indicator */}
            {sending && (
              <div className="flex items-start gap-3">
                <div className="w-8 h-8 rounded-full bg-primary/10 text-primary border border-primary/20 flex items-center justify-center shrink-0">
                  <span className="material-symbols-outlined text-[16px] animate-spin">
                    progress_activity
                  </span>
                </div>
                <div className="p-3.5 rounded-2xl rounded-tl-none bg-[var(--surface-container-low)] border border-[var(--outline-variant)] text-xs text-muted-foreground flex items-center gap-2">
                  <div className="w-2 h-2 rounded-full bg-primary animate-ping" />
                  Searching course materials & generating grounded answer...
                </div>
              </div>
            )}

            {/* Error Banner */}
            {error && (
              <div className="p-3 rounded-xl bg-destructive/10 border border-destructive/20 text-destructive text-xs font-semibold flex items-center justify-between">
                <span>{error}</span>
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => handleSendMessage()}
                  className="h-6 text-xs text-destructive hover:bg-destructive/20"
                >
                  Retry
                </Button>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>

          {/* Bottom Chat Prompt Input */}
          <div className="p-3 md:p-4 border-t border-[var(--outline-variant)] bg-[var(--surface-container-low)]">
            <form
              onSubmit={(e) => {
                e.preventDefault();
                handleSendMessage();
              }}
              className="flex items-end gap-2"
            >
              <div className="flex-1 relative">
                <Textarea
                  value={inputQuery}
                  onChange={(e) => setInputQuery(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder={`Ask a question about ${subject?.subject_name || "course topics"}... (Press Enter to send)`}
                  disabled={sending}
                  rows={2}
                  className="resize-none pr-10 text-xs md:text-sm bg-background"
                />
              </div>

              <Button
                type="submit"
                disabled={sending || !inputQuery.trim()}
                className="h-10 px-4 bg-primary text-white font-bold text-xs gap-1.5 shrink-0 cursor-pointer shadow-xs"
              >
                {sending ? (
                  <div className="w-4 h-4 border-2 border-t-transparent border-white rounded-full animate-spin" />
                ) : (
                  <>
                    <span>Send</span>
                    <span className="material-symbols-outlined text-[16px]">send</span>
                  </>
                )}
              </Button>
            </form>
            <div className="flex items-center justify-between text-[10px] text-muted-foreground mt-1.5 px-1">
              <span>Answers are referenced directly against your subject curriculum.</span>
              <span className="hidden sm:inline">Shift + Enter for new line</span>
            </div>
          </div>
        </div>
      </div>

      {/* Delete Conversation Confirmation Dialog */}
      <Dialog open={deleteModalOpen} onOpenChange={setDeleteModalOpen}>
        <DialogContent className="sm:max-w-[400px]">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-destructive">
              <span className="material-symbols-outlined text-[20px]">delete</span>
              Delete Conversation
            </DialogTitle>
            <DialogDescription>
              Are you sure you want to delete this chat thread? All messages in this conversation
              will be permanently removed.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter className="gap-2 pt-3">
            <Button
              type="button"
              variant="outline"
              onClick={() => setDeleteModalOpen(false)}
              disabled={deleting}
              className="text-xs"
            >
              Cancel
            </Button>
            <Button
              type="button"
              variant="destructive"
              onClick={handleDeleteConversation}
              disabled={deleting}
              className="text-xs font-bold"
            >
              {deleting ? "Deleting..." : "Delete Chat"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
