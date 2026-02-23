import { useNavigate } from "react-router-dom";
import {
  Box, Button, Container, Typography, Grid, Card, CardContent, Stack,
} from "@mui/material";
import {
  RecordVoiceOver, Build, Chat, Videocam,
} from "@mui/icons-material";

const features = [
  { icon: <RecordVoiceOver fontSize="large" color="primary" />, title: "Record Engine Sounds", desc: "Upload an audio clip of the issue — let mechanics hear exactly what's wrong." },
  { icon: <Build fontSize="large" color="secondary" />, title: "Get Expert Diagnoses", desc: "Verified mechanics respond with their diagnosis, cost estimate, and fix time." },
  { icon: <Chat fontSize="large" color="primary" />, title: "Chat in Real-Time", desc: "Discuss details with mechanics through instant messaging." },
  { icon: <Videocam fontSize="large" color="secondary" />, title: "Video Consultations", desc: "Show the issue live via video call for the most accurate diagnosis." },
];

export default function LandingPage() {
  const navigate = useNavigate();

  return (
    <Box>
      {/* Hero */}
      <Box sx={{
        background: "linear-gradient(135deg, #0d47a1 0%, #1565c0 50%, #1976d2 100%)",
        color: "white", py: { xs: 8, md: 14 }, textAlign: "center",
      }}>
        <Container maxWidth="md">
          <Typography variant="h3" fontWeight={800} gutterBottom>
            🚗 Car Trouble? Get a Diagnosis in Minutes
          </Typography>
          <Typography variant="h6" sx={{ opacity: 0.9, mb: 4, maxWidth: 600, mx: "auto" }}>
            Post your car issue with photos, videos, or audio of the engine sound.
            Verified mechanics will diagnose it — fast and affordable.
          </Typography>
          <Stack direction="row" spacing={2} justifyContent="center">
            <Button variant="contained" size="large" color="secondary"
              onClick={() => navigate("/signup")}
              sx={{ px: 4, py: 1.5, fontSize: "1.1rem" }}>
              Get a Diagnosis
            </Button>
            <Button variant="outlined" size="large" sx={{ color: "white", borderColor: "white", px: 4, py: 1.5 }}
              onClick={() => navigate("/signup")}>
              I'm a Mechanic
            </Button>
          </Stack>
        </Container>
      </Box>

      {/* How it works */}
      <Container maxWidth="lg" sx={{ py: 10 }}>
        <Typography variant="h4" textAlign="center" gutterBottom>
          How It Works
        </Typography>
        <Typography variant="body1" textAlign="center" color="text.secondary" sx={{ mb: 6 }}>
          Three simple steps to get expert help with your car
        </Typography>

        <Grid container spacing={4}>
          {[
            { step: "1", title: "Post Your Issue", desc: "Describe the problem, upload audio of the engine, add photos or videos." },
            { step: "2", title: "Mechanics Respond", desc: "Verified mechanics review your issue and send their diagnosis with cost estimates." },
            { step: "3", title: "Chat & Resolve", desc: "Discuss with the mechanic via chat or video call. Get the fix you need." },
          ].map((s) => (
            <Grid size={{ xs: 12, md: 4 }} key={s.step}>
              <Card sx={{ textAlign: "center", p: 3, height: "100%" }}>
                <Box sx={{
                  width: 56, height: 56, borderRadius: "50%", bgcolor: "primary.main",
                  color: "white", display: "flex", alignItems: "center", justifyContent: "center",
                  mx: "auto", mb: 2, fontSize: "1.5rem", fontWeight: 700,
                }}>
                  {s.step}
                </Box>
                <Typography variant="h6" gutterBottom>{s.title}</Typography>
                <Typography color="text.secondary">{s.desc}</Typography>
              </Card>
            </Grid>
          ))}
        </Grid>
      </Container>

      {/* Features */}
      <Box sx={{ bgcolor: "grey.50", py: 10 }}>
        <Container maxWidth="lg">
          <Typography variant="h4" textAlign="center" gutterBottom>
            Features
          </Typography>
          <Grid container spacing={4} sx={{ mt: 2 }}>
            {features.map((f) => (
              <Grid size={{ xs: 12, sm: 6 }} key={f.title}>
                <Card sx={{ p: 3, height: "100%" }}>
                  <CardContent>
                    <Stack direction="row" spacing={2} alignItems="center" mb={1}>
                      {f.icon}
                      <Typography variant="h6">{f.title}</Typography>
                    </Stack>
                    <Typography color="text.secondary">{f.desc}</Typography>
                  </CardContent>
                </Card>
              </Grid>
            ))}
          </Grid>
        </Container>
      </Box>

      {/* CTA */}
      <Box sx={{ textAlign: "center", py: 8 }}>
        <Typography variant="h5" gutterBottom>Ready to get your car diagnosed?</Typography>
        <Button variant="contained" size="large" onClick={() => navigate("/signup")} sx={{ mt: 2 }}>
          Sign Up Free
        </Button>
      </Box>
    </Box>
  );
}
