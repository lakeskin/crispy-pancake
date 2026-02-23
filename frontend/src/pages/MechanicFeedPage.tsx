import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import {
  Box, Typography, Card, CardContent, Chip, Grid, TextField, MenuItem,
  Stack, Pagination, CircularProgress, Alert, InputAdornment, Button, Divider,
} from "@mui/material";
import { Search, FilterList, LocationOn, AccessTime } from "@mui/icons-material";
import api from "../services/api";
import type { CarIssue } from "../types";

const CATEGORIES = [
  { id: "", label: "All Categories" },
  { id: "engine", label: "Engine" },
  { id: "brakes", label: "Brakes" },
  { id: "electrical", label: "Electrical" },
  { id: "suspension", label: "Suspension" },
  { id: "ac", label: "AC / Heating" },
  { id: "transmission", label: "Transmission" },
  { id: "body", label: "Body / Paint" },
  { id: "other", label: "Other" },
];

const URGENCY_OPTS = [
  { id: "", label: "All Urgency" },
  { id: "low", label: "Low" },
  { id: "normal", label: "Normal" },
  { id: "urgent", label: "Urgent" },
];

const urgencyColor: Record<string, "success" | "warning" | "error"> = {
  low: "success", normal: "warning", urgent: "error",
};

export default function MechanicFeedPage() {
  const navigate = useNavigate();
  const [issues, setIssues] = useState<CarIssue[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);

  // Filters
  const [category, setCategory] = useState("");
  const [urgency, setUrgency] = useState("");
  const [city, setCity] = useState("");

  useEffect(() => {
    fetchIssues();
  }, [page, category, urgency, city]);

  const fetchIssues = async () => {
    setLoading(true);
    try {
      const params: Record<string, any> = {
        status: "open",
        page,
        per_page: 10,
      };
      if (category) params.category = category;
      if (urgency) params.urgency = urgency;
      if (city) params.city = city;

      const res = await api.get("/issues", { params });
      setIssues(res.data.issues || res.data);
      setTotalPages(res.data.total_pages || 1);
    } catch (err: any) {
      setError(err.response?.data?.detail || "Failed to load issues");
    } finally {
      setLoading(false);
    }
  };

  const timeAgo = (dateStr: string) => {
    const diff = Date.now() - new Date(dateStr).getTime();
    const hours = Math.floor(diff / 3600000);
    if (hours < 1) return "Just now";
    if (hours < 24) return `${hours}h ago`;
    return `${Math.floor(hours / 24)}d ago`;
  };

  return (
    <Box>
      <Typography variant="h5" fontWeight={700} gutterBottom>Open Issues Feed</Typography>
      <Typography variant="body2" color="text.secondary" mb={3}>
        Browse issues from car owners and offer your expertise
      </Typography>

      {/* Filters */}
      <Card variant="outlined" sx={{ p: 2, mb: 3 }}>
        <Grid container spacing={2} alignItems="center">
          <Grid size={{ xs: 12, sm: 4 }}>
            <TextField select fullWidth size="small" value={category}
              onChange={(e) => { setCategory(e.target.value); setPage(1); }}
              InputProps={{ startAdornment: <InputAdornment position="start"><FilterList fontSize="small" /></InputAdornment> }}>
              {CATEGORIES.map((c) => <MenuItem key={c.id} value={c.id}>{c.label}</MenuItem>)}
            </TextField>
          </Grid>
          <Grid size={{ xs: 12, sm: 4 }}>
            <TextField select fullWidth size="small" value={urgency}
              onChange={(e) => { setUrgency(e.target.value); setPage(1); }}>
              {URGENCY_OPTS.map((u) => <MenuItem key={u.id} value={u.id}>{u.label}</MenuItem>)}
            </TextField>
          </Grid>
          <Grid size={{ xs: 12, sm: 4 }}>
            <TextField fullWidth size="small" placeholder="Filter by city…" value={city}
              onChange={(e) => { setCity(e.target.value); setPage(1); }}
              InputProps={{ startAdornment: <InputAdornment position="start"><LocationOn fontSize="small" /></InputAdornment> }} />
          </Grid>
        </Grid>
      </Card>

      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

      {loading ? (
        <Box display="flex" justifyContent="center" py={6}><CircularProgress /></Box>
      ) : issues.length === 0 ? (
        <Card variant="outlined" sx={{ p: 4, textAlign: "center" }}>
          <Typography color="text.secondary">No open issues matching your filters.</Typography>
        </Card>
      ) : (
        <Stack spacing={2}>
          {issues.map((issue) => (
            <Card key={issue.id} sx={{ cursor: "pointer", "&:hover": { boxShadow: 4 }, transition: "box-shadow 0.2s" }}
              onClick={() => navigate(`/issues/${issue.id}`)}>
              <CardContent>
                <Stack direction="row" justifyContent="space-between" alignItems="flex-start">
                  <Box flex={1}>
                    <Stack direction="row" spacing={1} mb={0.5}>
                      <Chip label={issue.category} size="small" color="primary" variant="outlined" />
                      <Chip label={issue.urgency} size="small" color={urgencyColor[issue.urgency] || "default"} />
                    </Stack>
                    <Typography variant="h6" fontWeight={600}>{issue.title}</Typography>
                    <Typography variant="body2" color="text.secondary" sx={{
                      overflow: "hidden", textOverflow: "ellipsis",
                      display: "-webkit-box", WebkitLineClamp: 2, WebkitBoxOrient: "vertical",
                    }}>
                      {issue.description}
                    </Typography>
                  </Box>
                  <Stack alignItems="flex-end" spacing={0.5} ml={2}>
                    <Stack direction="row" spacing={0.5} alignItems="center">
                      <AccessTime fontSize="small" color="action" />
                      <Typography variant="caption" color="text.secondary">
                        {timeAgo(issue.created_at)}
                      </Typography>
                    </Stack>
                    {issue.response_count != null && (
                      <Typography variant="caption" color="text.secondary">
                        {issue.response_count} response{issue.response_count !== 1 ? "s" : ""}
                      </Typography>
                    )}
                  </Stack>
                </Stack>
                <Divider sx={{ my: 1 }} />
                <Stack direction="row" spacing={2} alignItems="center">
                  <Typography variant="body2">
                    <strong>{issue.car_make} {issue.car_model}</strong> {issue.car_year}
                  </Typography>
                  {issue.location_city && (
                    <Stack direction="row" spacing={0.5} alignItems="center">
                      <LocationOn fontSize="small" color="action" />
                      <Typography variant="body2" color="text.secondary">{issue.location_city}</Typography>
                    </Stack>
                  )}
                  {issue.budget_range && (
                    <Chip label={issue.budget_range.replace("_", " ")} size="small" variant="outlined" />
                  )}
                </Stack>
              </CardContent>
            </Card>
          ))}

          {totalPages > 1 && (
            <Box display="flex" justifyContent="center" py={2}>
              <Pagination count={totalPages} page={page} onChange={(_, v) => setPage(v)} color="primary" />
            </Box>
          )}
        </Stack>
      )}
    </Box>
  );
}
