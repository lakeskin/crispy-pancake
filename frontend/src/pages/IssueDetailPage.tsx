import { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import {
  Box, Typography, Card, CardContent, Chip, Divider, Grid, Button,
  Stack, Avatar, CircularProgress, Alert, TextField, Rating, Dialog,
  DialogTitle, DialogContent, DialogActions, Paper,
} from "@mui/material";
import {
  ArrowBack, Chat, VideoCall, LocationOn, AccessTime, DirectionsCar,
  Mic, PhotoCamera, Videocam, Send,
} from "@mui/icons-material";
import api from "../services/api";
import { supabase } from "../services/supabase";
import { useAuth } from "../contexts/AuthContext";
import type { CarIssue, MechanicResponse, IssueMedia } from "../types";

const urgencyColor: Record<string, "success" | "warning" | "error"> = {
  low: "success", normal: "warning", urgent: "error",
};

export default function IssueDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { user } = useAuth();
  const [issue, setIssue] = useState<CarIssue | null>(null);
  const [responses, setResponses] = useState<MechanicResponse[]>([]);
  const [media, setMedia] = useState<IssueMedia[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  // Mechanic response dialog
  const [dialogOpen, setDialogOpen] = useState(false);
  const [respDiagnosis, setRespDiagnosis] = useState("");
  const [respCost, setRespCost] = useState("");
  const [respTime, setRespTime] = useState("");
  const [respConfidence, setRespConfidence] = useState("medium");
  const [respSubmitting, setRespSubmitting] = useState(false);

  useEffect(() => {
    fetchIssue();
  }, [id]);

  const fetchIssue = async () => {
    try {
      const res = await api.get(`/issues/${id}`);
      setIssue(res.data);
      setMedia(res.data.issue_media || []);
      const respRes = await api.get(`/issues/${id}/responses`);
      setResponses(respRes.data.responses || []);
    } catch (err: any) {
      setError(err.response?.data?.detail || "Issue not found");
    } finally {
      setLoading(false);
    }
  };

  const getMediaUrl = (storagePath: string) => {
    const { data } = supabase.storage.from("issue-media").getPublicUrl(storagePath);
    return data.publicUrl;
  };

  const handleRespond = async () => {
    setRespSubmitting(true);
    try {
      await api.post(`/issues/${id}/responses`, {
        initial_diagnosis: respDiagnosis,
        estimated_cost_min: parseFloat(respCost) || null,
        estimated_fix_time: respTime || null,
        confidence_level: respConfidence,
      });
      setDialogOpen(false);
      setRespDiagnosis(""); setRespCost(""); setRespTime("");
      fetchIssue();
    } catch (err: any) {
      setError(err.response?.data?.detail || "Failed to submit response");
    } finally {
      setRespSubmitting(false);
    }
  };

  const startConversation = async (mechanicId: string) => {
    try {
      const res = await api.post("/conversations", {
        issue_id: id,
        mechanic_id: mechanicId,
      });
      navigate(`/conversations/${res.data.id}`);
    } catch (err: any) {
      if (err.response?.status === 409) {
        // Conversation already exists
        navigate(`/conversations/${err.response.data.conversation_id}`);
      } else {
        setError("Failed to start conversation");
      }
    }
  };

  if (loading) return <Box display="flex" justifyContent="center" py={6}><CircularProgress /></Box>;
  if (!issue) return <Alert severity="error">{error || "Issue not found"}</Alert>;

  const isMechanic = user?.role === "mechanic";
  const isOwner = user?.id === issue.customer_id;

  return (
    <Box maxWidth={800} mx="auto">
      <Button startIcon={<ArrowBack />} onClick={() => navigate(-1)} sx={{ mb: 2 }}>Back</Button>

      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

      {/* Issue Header */}
      <Card sx={{ mb: 3 }}>
        <CardContent sx={{ p: 3 }}>
          <Stack direction="row" justifyContent="space-between" alignItems="flex-start">
            <Box flex={1}>
              <Stack direction="row" spacing={1} mb={1}>
                <Chip label={issue.category} size="small" color="primary" variant="outlined" />
                <Chip label={issue.urgency} size="small" color={urgencyColor[issue.urgency] || "default"} />
                <Chip label={issue.status} size="small" variant="outlined" />
              </Stack>
              <Typography variant="h5" fontWeight={700} gutterBottom>{issue.title}</Typography>
              <Typography variant="body1" color="text.secondary" whiteSpace="pre-wrap">
                {issue.description}
              </Typography>
            </Box>
          </Stack>

          <Divider sx={{ my: 2 }} />

          {/* Car details */}
          <Grid container spacing={2}>
            <Grid size={{ xs: 6, sm: 3 }}>
              <Stack direction="row" spacing={1} alignItems="center">
                <DirectionsCar fontSize="small" color="action" />
                <Box>
                  <Typography variant="caption" color="text.secondary">Car</Typography>
                  <Typography variant="body2" fontWeight={600}>
                    {issue.car_make} {issue.car_model} {issue.car_year}
                  </Typography>
                </Box>
              </Stack>
            </Grid>
            {issue.car_mileage && (
              <Grid size={{ xs: 6, sm: 3 }}>
                <Typography variant="caption" color="text.secondary">Mileage</Typography>
                <Typography variant="body2" fontWeight={600}>{issue.car_mileage?.toLocaleString()} km</Typography>
              </Grid>
            )}
            <Grid size={{ xs: 6, sm: 3 }}>
              <Typography variant="caption" color="text.secondary">Budget</Typography>
              <Typography variant="body2" fontWeight={600}>{issue.budget_range?.replace("_", " ") || "—"}</Typography>
            </Grid>
            {issue.location_city && (
              <Grid size={{ xs: 6, sm: 3 }}>
                <Stack direction="row" spacing={0.5} alignItems="center">
                  <LocationOn fontSize="small" color="action" />
                  <Typography variant="body2" fontWeight={600}>{issue.location_city}</Typography>
                </Stack>
              </Grid>
            )}
          </Grid>
        </CardContent>
      </Card>

      {/* Media */}
      {media.length > 0 && (
        <Card sx={{ mb: 3 }}>
          <CardContent>
            <Typography variant="h6" gutterBottom>Attached Media</Typography>
            <Grid container spacing={2}>
              {media.map((m) => (
                <Grid size={{ xs: 6, sm: 4 }} key={m.id}>
                  <Paper variant="outlined" sx={{ p: 1, textAlign: "center" }}>
                    {m.media_type === "image" ? (
                      <Box component="img" src={getMediaUrl(m.storage_path)}
                        sx={{ width: "100%", height: 150, objectFit: "cover", borderRadius: 1 }} />
                    ) : m.media_type === "audio" ? (
                      <Box>
                        <Mic sx={{ fontSize: 40, color: "primary.main", my: 1 }} />
                        <audio controls src={getMediaUrl(m.storage_path)} style={{ width: "100%" }} />
                      </Box>
                    ) : (
                      <Box>
                        <Videocam sx={{ fontSize: 40, color: "primary.main", my: 1 }} />
                        <video controls src={getMediaUrl(m.storage_path)} style={{ width: "100%", maxHeight: 150 }} />
                      </Box>
                    )}
                    <Typography variant="caption" color="text.secondary">{m.file_name}</Typography>
                  </Paper>
                </Grid>
              ))}
            </Grid>
          </CardContent>
        </Card>
      )}

      {/* Mechanic Respond Button */}
      {isMechanic && issue.status === "open" && (
        <Button variant="contained" fullWidth sx={{ mb: 3 }} onClick={() => setDialogOpen(true)}>
          Submit Your Diagnosis
        </Button>
      )}

      {/* Responses */}
      <Typography variant="h6" gutterBottom>
        {responses.length} Mechanic Response{responses.length !== 1 ? "s" : ""}
      </Typography>

      {responses.length === 0 && (
        <Card variant="outlined" sx={{ p: 3, textAlign: "center" }}>
          <Typography color="text.secondary">No responses yet. Check back soon!</Typography>
        </Card>
      )}

      {responses.map((r) => (
        <Card key={r.id} sx={{ mb: 2 }}>
          <CardContent>
            <Stack direction="row" spacing={2} alignItems="center" mb={2}>
              <Avatar sx={{ bgcolor: "primary.main" }}>
                {(r as any).mechanic_name?.[0] || "M"}
              </Avatar>
              <Box flex={1}>
                <Typography fontWeight={600}>{(r as any).mechanic_name || "Mechanic"}</Typography>
                <Stack direction="row" spacing={1} alignItems="center">
                  <Rating value={(r as any).mechanic_rating || 0} readOnly size="small" precision={0.5} />
                  <Chip label={r.confidence_level} size="small" variant="outlined" />
                </Stack>
              </Box>
              {isOwner && (
                <Stack direction="row" spacing={1}>
                  <Button size="small" variant="outlined" startIcon={<Chat />}
                    onClick={() => startConversation(r.mechanic_id)}>
                    Chat
                  </Button>
                </Stack>
              )}
            </Stack>
            <Typography variant="body1" whiteSpace="pre-wrap" mb={1}>
              {r.initial_diagnosis}
            </Typography>
            <Stack direction="row" spacing={2}>
              {r.estimated_cost_min != null && (
                <Chip label={`AED ${r.estimated_cost_min}${r.estimated_cost_max ? ` - ${r.estimated_cost_max}` : ''}`} size="small" color="success" variant="outlined" />
              )}
              {r.estimated_fix_time && (
                <Chip icon={<AccessTime />} label={r.estimated_fix_time} size="small" variant="outlined" />
              )}
            </Stack>
          </CardContent>
        </Card>
      ))}

      {/* Respond Dialog */}
      <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Submit Your Diagnosis</DialogTitle>
        <DialogContent>
          <TextField fullWidth multiline rows={4} label="Diagnosis / Recommendation" sx={{ mt: 1 }}
            value={respDiagnosis} onChange={(e) => setRespDiagnosis(e.target.value)}
            placeholder="What do you think is wrong? What would you recommend?" />
          <Grid container spacing={2} mt={1}>
            <Grid size={{ xs: 6 }}>
              <TextField fullWidth label="Estimated Cost (AED)" type="number"
                value={respCost} onChange={(e) => setRespCost(e.target.value)} />
            </Grid>
            <Grid size={{ xs: 6 }}>
              <TextField fullWidth label="Estimated Time" value={respTime}
                onChange={(e) => setRespTime(e.target.value)} placeholder="e.g. 2-3 hours" />
            </Grid>
            <Grid size={{ xs: 12 }}>
              <TextField select fullWidth label="Confidence Level" value={respConfidence}
                onChange={(e) => setRespConfidence(e.target.value)}>
                <option value="low">Low — Need to see the car</option>
                <option value="medium">Medium — Fairly confident</option>
                <option value="high">High — Very confident</option>
              </TextField>
            </Grid>
          </Grid>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDialogOpen(false)}>Cancel</Button>
          <Button variant="contained" disabled={!respDiagnosis.trim() || respSubmitting}
            onClick={handleRespond}>
            {respSubmitting ? "Submitting…" : "Submit"}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
