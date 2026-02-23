import { useState, useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import {
  Box, Typography, Stepper, Step, StepLabel, TextField, Button, Card,
  CardContent, MenuItem, Grid, Alert, IconButton, Stack, Chip, LinearProgress,
} from "@mui/material";
import {
  Mic, Stop, Delete, CloudUpload, PhotoCamera, Videocam, CheckCircle,
} from "@mui/icons-material";
import api from "../services/api";
import { useAuth } from "../contexts/AuthContext";

const STEPS = ["Describe the Issue", "Car Details", "Upload Media", "Review & Post"];

const CATEGORIES = [
  { id: "engine", label: "🔧 Engine" },
  { id: "brakes", label: "🛑 Brakes" },
  { id: "electrical", label: "⚡ Electrical" },
  { id: "suspension", label: "🔩 Suspension" },
  { id: "ac", label: "❄️ AC / Heating" },
  { id: "transmission", label: "⚙️ Transmission" },
  { id: "body", label: "🚗 Body / Paint" },
  { id: "other", label: "❓ Other" },
];

const URGENCY = [
  { id: "low", label: "Low — Can wait a few weeks", color: "#4caf50" },
  { id: "normal", label: "Normal — This week ideally", color: "#ff9800" },
  { id: "urgent", label: "Urgent — Needs attention now", color: "#f44336" },
];

const BUDGETS = [
  { id: "under_50", label: "Under AED 50" },
  { id: "50_200", label: "AED 50 - 200" },
  { id: "200_500", label: "AED 200 - 500" },
  { id: "above_500", label: "Above AED 500" },
  { id: "not_sure", label: "Not sure" },
];

interface MediaFile {
  file: File;
  type: "audio" | "image" | "video";
  preview?: string;
  uploaded?: boolean;
  storagePath?: string;
}

export default function CreateIssuePage() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [step, setStep] = useState(0);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  // Step 1
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [category, setCategory] = useState("");
  const [urgency, setUrgency] = useState("normal");

  // Step 2
  const [carMake, setCarMake] = useState("");
  const [carModel, setCarModel] = useState("");
  const [carYear, setCarYear] = useState("");
  const [carMileage, setCarMileage] = useState("");
  const [budget, setBudget] = useState("not_sure");
  const [city, setCity] = useState(user?.city || "");

  // Step 3 — media
  const [mediaFiles, setMediaFiles] = useState<MediaFile[]>([]);
  const [recording, setRecording] = useState(false);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);

  // Audio recording
  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream, { mimeType: "audio/webm" });
      chunksRef.current = [];
      recorder.ondataavailable = (e) => { if (e.data.size > 0) chunksRef.current.push(e.data); };
      recorder.onstop = () => {
        const blob = new Blob(chunksRef.current, { type: "audio/webm" });
        const file = new File([blob], `recording_${Date.now()}.webm`, { type: "audio/webm" });
        setMediaFiles((prev) => [...prev, { file, type: "audio" }]);
        stream.getTracks().forEach((t) => t.stop());
      };
      recorder.start();
      mediaRecorderRef.current = recorder;
      setRecording(true);

      // Auto-stop after 60s
      setTimeout(() => { if (mediaRecorderRef.current?.state === "recording") stopRecording(); }, 60000);
    } catch {
      setError("Microphone access denied. Please allow microphone access.");
    }
  };

  const stopRecording = () => {
    mediaRecorderRef.current?.stop();
    setRecording(false);
  };

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>, type: "image" | "video") => {
    const files = e.target.files;
    if (!files) return;
    Array.from(files).forEach((file) => {
      const preview = type === "image" ? URL.createObjectURL(file) : undefined;
      setMediaFiles((prev) => [...prev, { file, type, preview }]);
    });
  };

  const removeMedia = (idx: number) => {
    setMediaFiles((prev) => prev.filter((_, i) => i !== idx));
  };

  // Validation per step
  const canNext = () => {
    if (step === 0) return title.trim() && description.trim() && category;
    if (step === 1) return carMake.trim() && carModel.trim() && carYear;
    return true;
  };

  // Submit
  const handleSubmit = async () => {
    setLoading(true);
    setError("");
    try {
      // 1. Create the issue
      const issueRes = await api.post("/issues", {
        title, description, category, urgency,
        car_make: carMake, car_model: carModel,
        car_year: parseInt(carYear),
        car_mileage: carMileage ? parseInt(carMileage) : null,
        budget_range: budget, location_city: city || null,
      });
      const issue = issueRes.data;

      // 2. Upload media files via backend proxy & register
      for (const media of mediaFiles) {
        try {
          const formData = new FormData();
          formData.append("file", media.file);
          formData.append("issue_id", issue.id);

          const uploadRes = await api.post("/uploads/issue-media", formData, {
            headers: { "Content-Type": "multipart/form-data" },
          });

          // Register media in DB
          await api.post(`/issues/${issue.id}/media`, {
            media_type: media.type,
            storage_path: uploadRes.data.storage_path,
            file_name: uploadRes.data.file_name || media.file.name,
            file_size: uploadRes.data.file_size || media.file.size,
          });
        } catch (uploadErr) {
          console.error("Upload error:", uploadErr);
        }
      }

      navigate(`/issues/${issue.id}`);
    } catch (err: any) {
      setError(err.response?.data?.detail || "Failed to create issue");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Box maxWidth={700} mx="auto">
      <Typography variant="h5" gutterBottom fontWeight={700}>Post a Car Issue</Typography>

      <Stepper activeStep={step} sx={{ mb: 4 }}>
        {STEPS.map((label) => (
          <Step key={label}><StepLabel>{label}</StepLabel></Step>
        ))}
      </Stepper>

      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}
      {loading && <LinearProgress sx={{ mb: 2 }} />}

      <Card>
        <CardContent sx={{ p: 3 }}>
          {/* ---------- STEP 0: Describe ---------- */}
          {step === 0 && (
            <Box>
              <TextField fullWidth label="What's wrong with your car?" value={title}
                onChange={(e) => setTitle(e.target.value)} sx={{ mb: 2 }}
                placeholder="e.g. Strange grinding noise when braking" />
              <TextField fullWidth multiline rows={4} label="Describe the issue in detail"
                value={description} onChange={(e) => setDescription(e.target.value)} sx={{ mb: 2 }}
                placeholder="When does it happen? How long has it been going on?" />
              <TextField select fullWidth label="Category" value={category}
                onChange={(e) => setCategory(e.target.value)} sx={{ mb: 2 }}>
                {CATEGORIES.map((c) => <MenuItem key={c.id} value={c.id}>{c.label}</MenuItem>)}
              </TextField>
              <Typography variant="body2" fontWeight={600} mb={1}>Urgency</Typography>
              <Stack direction="row" spacing={1} flexWrap="wrap">
                {URGENCY.map((u) => (
                  <Chip key={u.id} label={u.label} variant={urgency === u.id ? "filled" : "outlined"}
                    onClick={() => setUrgency(u.id)}
                    sx={{ bgcolor: urgency === u.id ? u.color : undefined, color: urgency === u.id ? "white" : undefined }} />
                ))}
              </Stack>
            </Box>
          )}

          {/* ---------- STEP 1: Car Details ---------- */}
          {step === 1 && (
            <Box>
              <Grid container spacing={2}>
                <Grid size={{ xs: 6 }}>
                  <TextField fullWidth label="Make" value={carMake}
                    onChange={(e) => setCarMake(e.target.value)} placeholder="Toyota" />
                </Grid>
                <Grid size={{ xs: 6 }}>
                  <TextField fullWidth label="Model" value={carModel}
                    onChange={(e) => setCarModel(e.target.value)} placeholder="Camry" />
                </Grid>
                <Grid size={{ xs: 6 }}>
                  <TextField fullWidth label="Year" type="number" value={carYear}
                    onChange={(e) => setCarYear(e.target.value)} placeholder="2022" />
                </Grid>
                <Grid size={{ xs: 6 }}>
                  <TextField fullWidth label="Mileage (km)" type="number" value={carMileage}
                    onChange={(e) => setCarMileage(e.target.value)} placeholder="85000" />
                </Grid>
                <Grid size={{ xs: 12 }}>
                  <TextField select fullWidth label="Budget Range" value={budget}
                    onChange={(e) => setBudget(e.target.value)}>
                    {BUDGETS.map((b) => <MenuItem key={b.id} value={b.id}>{b.label}</MenuItem>)}
                  </TextField>
                </Grid>
                <Grid size={{ xs: 12 }}>
                  <TextField fullWidth label="City (optional)" value={city}
                    onChange={(e) => setCity(e.target.value)} placeholder="Dubai" />
                </Grid>
              </Grid>
            </Box>
          )}

          {/* ---------- STEP 2: Upload Media ---------- */}
          {step === 2 && (
            <Box>
              <Typography variant="body1" mb={2}>
                Help mechanics diagnose faster — upload audio, photos, or video of the issue.
              </Typography>

              {/* Audio recorder */}
              <Card variant="outlined" sx={{ p: 2, mb: 2 }}>
                <Stack direction="row" spacing={2} alignItems="center">
                  <Mic color={recording ? "error" : "primary"} />
                  <Typography flex={1}>Record Engine Sound</Typography>
                  {recording ? (
                    <Button variant="contained" color="error" startIcon={<Stop />} onClick={stopRecording}>
                      Stop Recording
                    </Button>
                  ) : (
                    <Button variant="outlined" startIcon={<Mic />} onClick={startRecording}>
                      Record
                    </Button>
                  )}
                </Stack>
              </Card>

              {/* Photo upload */}
              <Card variant="outlined" sx={{ p: 2, mb: 2 }}>
                <Stack direction="row" spacing={2} alignItems="center">
                  <PhotoCamera color="primary" />
                  <Typography flex={1}>Upload Photos</Typography>
                  <Button variant="outlined" component="label" startIcon={<CloudUpload />}>
                    Choose
                    <input hidden accept="image/*" multiple type="file"
                      onChange={(e) => handleFileUpload(e, "image")} />
                  </Button>
                </Stack>
              </Card>

              {/* Video upload */}
              <Card variant="outlined" sx={{ p: 2, mb: 2 }}>
                <Stack direction="row" spacing={2} alignItems="center">
                  <Videocam color="primary" />
                  <Typography flex={1}>Upload Video</Typography>
                  <Button variant="outlined" component="label" startIcon={<CloudUpload />}>
                    Choose
                    <input hidden accept="video/*" type="file"
                      onChange={(e) => handleFileUpload(e, "video")} />
                  </Button>
                </Stack>
              </Card>

              {/* Preview */}
              {mediaFiles.length > 0 && (
                <Box mt={2}>
                  <Typography variant="body2" fontWeight={600} mb={1}>
                    {mediaFiles.length} file(s) attached
                  </Typography>
                  <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
                    {mediaFiles.map((m, i) => (
                      <Chip key={i} label={`${m.type}: ${m.file.name.slice(0, 20)}…`}
                        onDelete={() => removeMedia(i)}
                        icon={m.type === "audio" ? <Mic /> : m.type === "image" ? <PhotoCamera /> : <Videocam />} />
                    ))}
                  </Stack>
                </Box>
              )}
            </Box>
          )}

          {/* ---------- STEP 3: Review ---------- */}
          {step === 3 && (
            <Box>
              <Typography variant="h6" gutterBottom>Review Your Issue</Typography>
              <Stack spacing={1}>
                <Typography><strong>Title:</strong> {title}</Typography>
                <Typography><strong>Description:</strong> {description}</Typography>
                <Typography><strong>Category:</strong> {category} | <strong>Urgency:</strong> {urgency}</Typography>
                <Typography><strong>Car:</strong> {carMake} {carModel} {carYear} {carMileage && `• ${carMileage} km`}</Typography>
                <Typography><strong>Budget:</strong> {BUDGETS.find(b => b.id === budget)?.label}</Typography>
                {city && <Typography><strong>City:</strong> {city}</Typography>}
                <Typography><strong>Media:</strong> {mediaFiles.length} file(s) attached</Typography>
              </Stack>
            </Box>
          )}

          {/* Navigation */}
          <Stack direction="row" justifyContent="space-between" mt={4}>
            <Button disabled={step === 0} onClick={() => setStep(step - 1)}>Back</Button>
            {step < 3 ? (
              <Button variant="contained" disabled={!canNext()} onClick={() => setStep(step + 1)}>
                Next
              </Button>
            ) : (
              <Button variant="contained" color="success" disabled={loading}
                startIcon={<CheckCircle />} onClick={handleSubmit}>
                {loading ? "Posting…" : "Post Issue"}
              </Button>
            )}
          </Stack>
        </CardContent>
      </Card>
    </Box>
  );
}
