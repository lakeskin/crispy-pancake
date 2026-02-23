import { useState } from "react";
import { useNavigate, Link as RouterLink } from "react-router-dom";
import {
  Box, Card, CardContent, Typography, TextField, Button, Alert, Link,
  Container, ToggleButtonGroup, ToggleButton, Stack,
} from "@mui/material";
import { Build, DirectionsCar } from "@mui/icons-material";
import { useAuth } from "../contexts/AuthContext";

export default function SignupPage() {
  const { signup } = useAuth();
  const navigate = useNavigate();

  const [role, setRole] = useState<"customer" | "mechanic">("customer");
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    if (password.length < 8) {
      setError("Password must be at least 8 characters");
      return;
    }
    setLoading(true);
    try {
      await signup(email, password, fullName, role);
      navigate("/dashboard");
    } catch (err: any) {
      setError(err.response?.data?.detail || "Signup failed. Try a different email.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Box sx={{
      minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center",
      background: "linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%)",
    }}>
      <Container maxWidth="xs">
        <Card>
          <CardContent sx={{ p: 4 }}>
            <Typography variant="h5" textAlign="center" gutterBottom fontWeight={700}>
              🚗 Join SalikChat
            </Typography>
            <Typography variant="body2" textAlign="center" color="text.secondary" mb={3}>
              Create your account
            </Typography>

            {/* Role selector */}
            <Box sx={{ mb: 3 }}>
              <Typography variant="body2" fontWeight={600} mb={1}>I am a:</Typography>
              <ToggleButtonGroup
                value={role}
                exclusive
                onChange={(_, v) => v && setRole(v)}
                fullWidth
                size="large"
              >
                <ToggleButton value="customer">
                  <Stack direction="row" spacing={1} alignItems="center">
                    <DirectionsCar fontSize="small" />
                    <span>Car Owner</span>
                  </Stack>
                </ToggleButton>
                <ToggleButton value="mechanic">
                  <Stack direction="row" spacing={1} alignItems="center">
                    <Build fontSize="small" />
                    <span>Mechanic</span>
                  </Stack>
                </ToggleButton>
              </ToggleButtonGroup>
            </Box>

            {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

            <form onSubmit={handleSubmit}>
              <TextField
                fullWidth label="Full Name" value={fullName}
                onChange={(e) => setFullName(e.target.value)} required sx={{ mb: 2 }}
              />
              <TextField
                fullWidth label="Email" type="email" value={email}
                onChange={(e) => setEmail(e.target.value)} required sx={{ mb: 2 }}
              />
              <TextField
                fullWidth label="Password" type="password" value={password}
                onChange={(e) => setPassword(e.target.value)} required
                helperText="At least 8 characters" sx={{ mb: 3 }}
              />
              <Button fullWidth variant="contained" type="submit" disabled={loading} size="large">
                {loading ? "Creating account…" : `Sign Up as ${role === "customer" ? "Car Owner" : "Mechanic"}`}
              </Button>
            </form>

            <Typography variant="body2" textAlign="center" sx={{ mt: 3 }}>
              Already have an account?{" "}
              <Link component={RouterLink} to="/login" underline="hover">
                Sign In
              </Link>
            </Typography>
          </CardContent>
        </Card>
      </Container>
    </Box>
  );
}
