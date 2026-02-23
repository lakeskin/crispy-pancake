import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Box, Typography, Grid, Card, CardContent, Button, Chip, Stack, Skeleton,
} from "@mui/material";
import { Add, Chat, Build, Search } from "@mui/icons-material";
import { useAuth } from "../contexts/AuthContext";
import api from "../services/api";
import type { CarIssue, Conversation } from "../types";

export default function DashboardPage() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const isMechanic = user?.role === "mechanic";

  const [issues, setIssues] = useState<CarIssue[]>([]);
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const load = async () => {
      try {
        const [issuesRes, convRes] = await Promise.all([
          isMechanic
            ? api.get("/issues", { params: { limit: 5 } })
            : api.get("/issues", { params: { my_issues: true, limit: 5 } }),
          api.get("/conversations"),
        ]);
        setIssues(issuesRes.data.issues || []);
        setConversations(convRes.data.conversations || []);
      } catch {
        // ignore
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [isMechanic]);

  const totalUnread = conversations.reduce((s, c) => s + (c.unread_count || 0), 0);

  if (loading) {
    return (
      <Box>
        <Skeleton variant="text" width={200} height={40} />
        <Grid container spacing={3} mt={1}>
          {[1, 2, 3].map((i) => (
            <Grid size={{ xs: 12, sm: 4 }} key={i}><Skeleton variant="rounded" height={120} /></Grid>
          ))}
        </Grid>
      </Box>
    );
  }

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Welcome, {user?.full_name || "User"} 👋
      </Typography>
      <Typography variant="body1" color="text.secondary" mb={3}>
        {isMechanic ? "Browse car issues and help car owners with diagnostics." : "Post a car issue and get expert mechanic advice."}
      </Typography>

      {/* Stats cards */}
      <Grid container spacing={3} mb={4}>
        <Grid size={{ xs: 6, sm: 3 }}>
          <Card>
            <CardContent sx={{ textAlign: "center" }}>
              <Typography variant="h4" color="primary">{issues.length}</Typography>
              <Typography variant="body2" color="text.secondary">
                {isMechanic ? "Open Issues" : "My Issues"}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid size={{ xs: 6, sm: 3 }}>
          <Card>
            <CardContent sx={{ textAlign: "center" }}>
              <Typography variant="h4" color="secondary">{conversations.length}</Typography>
              <Typography variant="body2" color="text.secondary">Conversations</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid size={{ xs: 6, sm: 3 }}>
          <Card>
            <CardContent sx={{ textAlign: "center" }}>
              <Typography variant="h4" color="error.main">{totalUnread}</Typography>
              <Typography variant="body2" color="text.secondary">Unread Messages</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid size={{ xs: 6, sm: 3 }}>
          <Card>
            <CardContent sx={{ textAlign: "center" }}>
              <Typography variant="h4" color="success.main">
                {isMechanic ? "⭐" : issues.filter(i => i.status === "resolved").length}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                {isMechanic ? "Rating" : "Resolved"}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Quick actions */}
      <Stack direction="row" spacing={2} mb={4}>
        {isMechanic ? (
          <Button variant="contained" startIcon={<Search />} onClick={() => navigate("/feed")}>
            Browse Issues
          </Button>
        ) : (
          <Button variant="contained" startIcon={<Add />} onClick={() => navigate("/issues/new")}>
            Post New Issue
          </Button>
        )}
        <Button variant="outlined" startIcon={<Chat />} onClick={() => navigate("/conversations")}>
          My Conversations {totalUnread > 0 && `(${totalUnread})`}
        </Button>
      </Stack>

      {/* Recent issues */}
      <Typography variant="h6" gutterBottom>
        {isMechanic ? "Recent Open Issues" : "My Recent Issues"}
      </Typography>
      {issues.length === 0 ? (
        <Card sx={{ p: 4, textAlign: "center" }}>
          <Typography color="text.secondary">
            {isMechanic ? "No open issues yet." : "You haven't posted any issues yet."}
          </Typography>
          {!isMechanic && (
            <Button variant="contained" sx={{ mt: 2 }} onClick={() => navigate("/issues/new")}>
              Post Your First Issue
            </Button>
          )}
        </Card>
      ) : (
        <Grid container spacing={2}>
          {issues.map((issue) => (
            <Grid size={{ xs: 12, md: 6 }} key={issue.id}>
              <Card
                sx={{ cursor: "pointer", "&:hover": { boxShadow: 6 } }}
                onClick={() => navigate(`/issues/${issue.id}`)}
              >
                <CardContent>
                  <Stack direction="row" justifyContent="space-between" alignItems="flex-start">
                    <Box>
                      <Typography variant="subtitle1" fontWeight={600}>{issue.title}</Typography>
                      <Typography variant="body2" color="text.secondary">
                        {issue.car_make} {issue.car_model} {issue.car_year}
                      </Typography>
                    </Box>
                    <Stack direction="row" spacing={1}>
                      <Chip
                        size="small"
                        label={issue.urgency}
                        color={issue.urgency === "urgent" ? "error" : issue.urgency === "normal" ? "warning" : "success"}
                      />
                      <Chip size="small" label={issue.status} variant="outlined" />
                    </Stack>
                  </Stack>
                  <Stack direction="row" spacing={1} mt={1}>
                    <Chip size="small" label={issue.category} icon={<Build sx={{ fontSize: 14 }} />} />
                    {(issue.response_count ?? 0) > 0 && (
                      <Chip size="small" label={`${issue.response_count} responses`} color="primary" variant="outlined" />
                    )}
                    {issue.issue_media && issue.issue_media.length > 0 && (
                      <Chip size="small" label={`${issue.issue_media.length} files`} variant="outlined" />
                    )}
                  </Stack>
                </CardContent>
              </Card>
            </Grid>
          ))}
        </Grid>
      )}
    </Box>
  );
}
