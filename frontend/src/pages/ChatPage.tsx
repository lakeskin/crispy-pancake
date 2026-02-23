import { useState, useEffect, useRef, useCallback } from "react";
import { useParams, useNavigate } from "react-router-dom";
import {
  Box, Typography, TextField, IconButton, Stack, Avatar, Card, CardContent,
  CircularProgress, Alert, Button, Paper, Divider, Chip,
} from "@mui/material";
import {
  ArrowBack, Send, AttachFile, Mic, Stop, Image as ImageIcon, Info,
} from "@mui/icons-material";
import api from "../services/api";
import { supabase } from "../services/supabase";
import { useAuth } from "../contexts/AuthContext";
import type { Message } from "../types";

export default function ChatPage() {
  const { id: conversationId } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { user } = useAuth();

  const [messages, setMessages] = useState<Message[]>([]);
  const [conversationInfo, setConversationInfo] = useState<any>(null);
  const [newMessage, setNewMessage] = useState("");
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState("");

  // Audio recording
  const [recording, setRecording] = useState(false);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);

  // Auto-scroll
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  // Fetch initial data
  useEffect(() => {
    const init = async () => {
      try {
        const [convRes, msgRes] = await Promise.all([
          api.get(`/conversations/${conversationId}`),
          api.get(`/conversations/${conversationId}/messages?per_page=100`),
        ]);
        setConversationInfo(convRes.data);
        setMessages(msgRes.data.messages || msgRes.data);

        // Mark messages as read
        api.post(`/conversations/${conversationId}/messages/read`).catch(() => {});
      } catch (err: any) {
        setError(err.response?.data?.detail || "Failed to load conversation");
      } finally {
        setLoading(false);
      }
    };
    init();
  }, [conversationId]);

  // ─── Supabase Realtime Subscription ───
  useEffect(() => {
    if (!conversationId) return;

    const channel = supabase
      .channel(`chat:${conversationId}`)
      .on(
        "postgres_changes",
        {
          event: "INSERT",
          schema: "public",
          table: "messages",
          filter: `conversation_id=eq.${conversationId}`,
        },
        (payload) => {
          const newMsg = payload.new as Message;
          setMessages((prev) => {
            // Deduplicate
            if (prev.some((m) => m.id === newMsg.id)) return prev;
            return [...prev, newMsg];
          });

          // Mark as read if it's from the other person
          if (newMsg.sender_id !== user?.id) {
            api.post(`/conversations/${conversationId}/messages/read`).catch(() => {});
          }
        }
      )
      .subscribe();

    return () => {
      supabase.removeChannel(channel);
    };
  }, [conversationId, user?.id]);

  // Auto-scroll on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Send text message
  const handleSend = async () => {
    const text = newMessage.trim();
    if (!text || sending) return;

    setNewMessage("");
    setSending(true);
    try {
      await api.post(`/conversations/${conversationId}/messages`, {
        content: text,
        message_type: "text",
      });
    } catch {
      setError("Failed to send message");
      setNewMessage(text);
    } finally {
      setSending(false);
    }
  };

  // Send image
  const handleImageUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setSending(true);
    try {
      const path = `chat/${conversationId}/${Date.now()}_${file.name}`;
      const { error: uploadErr } = await supabase.storage
        .from("chat-media")
        .upload(path, file, { contentType: file.type });

      if (uploadErr) throw uploadErr;

      const { data } = supabase.storage.from("chat-media").getPublicUrl(path);

      await api.post(`/conversations/${conversationId}/messages`, {
        content: data.publicUrl,
        message_type: "image",
      });
    } catch {
      setError("Failed to upload image");
    } finally {
      setSending(false);
    }
  };

  // Audio recording
  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream, { mimeType: "audio/webm" });
      chunksRef.current = [];
      recorder.ondataavailable = (e) => { if (e.data.size) chunksRef.current.push(e.data); };
      recorder.onstop = async () => {
        stream.getTracks().forEach((t) => t.stop());
        const blob = new Blob(chunksRef.current, { type: "audio/webm" });
        const file = new File([blob], `voice_${Date.now()}.webm`, { type: "audio/webm" });

        setSending(true);
        try {
          const path = `chat/${conversationId}/${file.name}`;
          const { error: uploadErr } = await supabase.storage
            .from("chat-media")
            .upload(path, file, { contentType: file.type });
          if (uploadErr) throw uploadErr;

          const { data } = supabase.storage.from("chat-media").getPublicUrl(path);
          await api.post(`/conversations/${conversationId}/messages`, {
            content: data.publicUrl,
            message_type: "audio",
          });
        } catch {
          setError("Failed to send voice message");
        } finally {
          setSending(false);
        }
      };
      recorder.start();
      mediaRecorderRef.current = recorder;
      setRecording(true);
      setTimeout(() => { if (mediaRecorderRef.current?.state === "recording") stopRecording(); }, 60000);
    } catch {
      setError("Microphone access denied");
    }
  };

  const stopRecording = () => {
    mediaRecorderRef.current?.stop();
    setRecording(false);
  };

  // Key handler
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  // Format timestamp
  const formatTime = (dateStr: string) => {
    const d = new Date(dateStr);
    return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  };

  const formatDate = (dateStr: string) => {
    const d = new Date(dateStr);
    const today = new Date();
    if (d.toDateString() === today.toDateString()) return "Today";
    const yesterday = new Date(today);
    yesterday.setDate(yesterday.getDate() - 1);
    if (d.toDateString() === yesterday.toDateString()) return "Yesterday";
    return d.toLocaleDateString();
  };

  // Group messages by date
  const groupedMessages: { date: string; msgs: Message[] }[] = [];
  messages.forEach((msg) => {
    const date = formatDate(msg.created_at);
    const last = groupedMessages[groupedMessages.length - 1];
    if (last?.date === date) {
      last.msgs.push(msg);
    } else {
      groupedMessages.push({ date, msgs: [msg] });
    }
  });

  if (loading) return <Box display="flex" justifyContent="center" py={6}><CircularProgress /></Box>;

  const otherName = conversationInfo?.customer_id === user?.id
    ? conversationInfo?.mechanic_name || "Mechanic"
    : conversationInfo?.customer_name || "Customer";

  return (
    <Box display="flex" flexDirection="column" height="calc(100vh - 80px)" maxWidth={800} mx="auto">
      {/* Header */}
      <Stack direction="row" alignItems="center" spacing={2} sx={{ pb: 1, borderBottom: 1, borderColor: "divider" }}>
        <IconButton onClick={() => navigate("/conversations")}><ArrowBack /></IconButton>
        <Avatar sx={{ bgcolor: "primary.main" }}>{otherName[0]}</Avatar>
        <Box flex={1}>
          <Typography fontWeight={600}>{otherName}</Typography>
          {conversationInfo?.issue_title && (
            <Typography variant="caption" color="text.secondary">
              Re: {conversationInfo.issue_title}
            </Typography>
          )}
        </Box>
      </Stack>

      {error && <Alert severity="error" sx={{ mt: 1 }}>{error}</Alert>}

      {/* Messages */}
      <Box ref={containerRef} flex={1} overflow="auto" py={2}
        sx={{ display: "flex", flexDirection: "column" }}>
        {groupedMessages.map((group) => (
          <Box key={group.date}>
            <Box display="flex" justifyContent="center" my={1}>
              <Chip label={group.date} size="small" variant="outlined" />
            </Box>
            {group.msgs.map((msg) => {
              const isMine = msg.sender_id === user?.id;
              const isSystem = msg.message_type === "system";

              if (isSystem) {
                return (
                  <Box key={msg.id} display="flex" justifyContent="center" my={1}>
                    <Typography variant="caption" color="text.secondary" fontStyle="italic">
                      {msg.content}
                    </Typography>
                  </Box>
                );
              }

              return (
                <Box key={msg.id} display="flex" justifyContent={isMine ? "flex-end" : "flex-start"} mb={0.5}>
                  <Paper elevation={0} sx={{
                    maxWidth: "75%",
                    px: 2, py: 1, borderRadius: 2,
                    bgcolor: isMine ? "primary.main" : "grey.100",
                    color: isMine ? "white" : "text.primary",
                    borderTopRightRadius: isMine ? 4 : 16,
                    borderTopLeftRadius: isMine ? 16 : 4,
                  }}>
                    {msg.message_type === "image" ? (
                      <Box component="img" src={msg.content}
                        sx={{ maxWidth: "100%", maxHeight: 250, borderRadius: 1, display: "block" }}
                        onClick={() => window.open(msg.content, "_blank")} />
                    ) : msg.message_type === "audio" ? (
                      <audio controls src={msg.content} style={{ maxWidth: "100%" }} />
                    ) : (
                      <Typography variant="body2" whiteSpace="pre-wrap">{msg.content}</Typography>
                    )}
                    <Typography variant="caption" sx={{
                      opacity: 0.7, display: "block", textAlign: "right", mt: 0.5,
                      color: isMine ? "rgba(255,255,255,0.7)" : "text.secondary",
                    }}>
                      {formatTime(msg.created_at)}
                      {isMine && msg.read_at && " ✓✓"}
                    </Typography>
                  </Paper>
                </Box>
              );
            })}
          </Box>
        ))}
        <div ref={messagesEndRef} />
      </Box>

      {/* Input bar */}
      <Stack direction="row" spacing={1} alignItems="flex-end"
        sx={{ pt: 1, borderTop: 1, borderColor: "divider" }}>
        {/* Image upload */}
        <IconButton component="label" size="small">
          <ImageIcon />
          <input hidden accept="image/*" type="file" onChange={handleImageUpload} />
        </IconButton>

        {/* Voice */}
        {recording ? (
          <IconButton color="error" onClick={stopRecording}><Stop /></IconButton>
        ) : (
          <IconButton onClick={startRecording}><Mic /></IconButton>
        )}

        <TextField fullWidth size="small" multiline maxRows={4} placeholder="Type a message…"
          value={newMessage} onChange={(e) => setNewMessage(e.target.value)}
          onKeyDown={handleKeyDown} disabled={sending}
          sx={{ "& .MuiOutlinedInput-root": { borderRadius: 3 } }} />

        <IconButton color="primary" onClick={handleSend} disabled={!newMessage.trim() || sending}>
          <Send />
        </IconButton>
      </Stack>
    </Box>
  );
}
