import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import {
  Box, Typography, List, ListItemButton, ListItemAvatar, Avatar, ListItemText,
  Badge, CircularProgress, Alert, Chip, Stack, Card, Divider,
} from "@mui/material";
import { Chat, DirectionsCar } from "@mui/icons-material";
import api from "../services/api";
import { supabase } from "../services/supabase";
import { useAuth } from "../contexts/AuthContext";
import type { Conversation } from "../types";

export default function ConversationsPage() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    fetchConversations();

    // Real-time subscription for conversation updates
    const channel = supabase
      .channel("conversations_page")
      .on("postgres_changes", {
        event: "*",
        schema: "public",
        table: "messages",
      }, () => {
        // Refresh on any message change
        fetchConversations();
      })
      .subscribe();

    return () => { supabase.removeChannel(channel); };
  }, []);

  const fetchConversations = async () => {
    try {
      const res = await api.get("/conversations");
      setConversations(res.data.conversations || []);
    } catch (err: any) {
      setError(err.response?.data?.detail || "Failed to load conversations");
    } finally {
      setLoading(false);
    }
  };

  const getOtherParty = (conv: Conversation) => {
    if (user?.role === "customer") {
      return { name: (conv as any).mechanic_name || "Mechanic", initials: "M" };
    }
    return { name: (conv as any).customer_name || "Customer", initials: "C" };
  };

  const timeAgo = (dateStr: string) => {
    if (!dateStr) return "";
    const diff = Date.now() - new Date(dateStr).getTime();
    const mins = Math.floor(diff / 60000);
    if (mins < 1) return "Now";
    if (mins < 60) return `${mins}m`;
    const hours = Math.floor(mins / 60);
    if (hours < 24) return `${hours}h`;
    return `${Math.floor(hours / 24)}d`;
  };

  if (loading) return <Box display="flex" justifyContent="center" py={6}><CircularProgress /></Box>;

  return (
    <Box>
      <Typography variant="h5" fontWeight={700} gutterBottom>Conversations</Typography>

      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

      {conversations.length === 0 ? (
        <Card variant="outlined" sx={{ p: 4, textAlign: "center" }}>
          <Chat sx={{ fontSize: 48, color: "text.disabled", mb: 1 }} />
          <Typography color="text.secondary">No conversations yet.</Typography>
          <Typography variant="body2" color="text.secondary">
            {user?.role === "customer"
              ? "Post an issue and chat with mechanics who respond."
              : "Browse open issues and offer your expertise to start a conversation."}
          </Typography>
        </Card>
      ) : (
        <Card>
          <List disablePadding>
            {conversations.map((conv, idx) => {
              const other = getOtherParty(conv);
              const unread = (conv as any).unread_count || 0;

              return (
                <Box key={conv.id}>
                  {idx > 0 && <Divider component="li" />}
                  <ListItemButton onClick={() => navigate(`/conversations/${conv.id}`)}
                    sx={{ py: 2 }}>
                    <ListItemAvatar>
                      <Badge badgeContent={unread} color="error" invisible={unread === 0}>
                        <Avatar sx={{ bgcolor: "primary.main" }}>{other.initials}</Avatar>
                      </Badge>
                    </ListItemAvatar>
                    <ListItemText
                      primary={
                        <Stack direction="row" justifyContent="space-between">
                          <Typography fontWeight={unread > 0 ? 700 : 400}>
                            {other.name}
                          </Typography>
                          <Typography variant="caption" color="text.secondary">
                            {timeAgo((conv as any).last_message_at || conv.updated_at)}
                          </Typography>
                        </Stack>
                      }
                      secondary={
                        <Stack direction="row" spacing={1} alignItems="center">
                          <DirectionsCar fontSize="small" color="action" />
                          <Typography variant="body2" color="text.secondary" noWrap sx={{ maxWidth: 300 }}>
                            {(conv as any).issue_title || "Chat"}
                          </Typography>
                        </Stack>
                      }
                    />
                  </ListItemButton>
                </Box>
              );
            })}
          </List>
        </Card>
      )}
    </Box>
  );
}
