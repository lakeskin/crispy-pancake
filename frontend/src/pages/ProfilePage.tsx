import { useState, useEffect } from "react";
import {
  Box, Typography, Card, CardContent, TextField, Button, Grid, Avatar,
  Stack, Chip, Switch, FormControlLabel, Alert, Divider, Rating,
  CircularProgress,
} from "@mui/material";
import { Save, Edit, LocationOn } from "@mui/icons-material";
import api from "../services/api";
import { useAuth } from "../contexts/AuthContext";

const SPECIALIZATIONS = [
  "engine_repair", "electrical_systems", "body_work", "ac_systems",
  "brake_systems", "transmission", "suspension", "diagnostics",
  "hybrid_ev", "general_maintenance",
];

export default function ProfilePage() {
  const { user } = useAuth();
  const [profile, setProfile] = useState<any>(null);
  const [mechanicProfile, setMechanicProfile] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [success, setSuccess] = useState("");
  const [error, setError] = useState("");
  const [editing, setEditing] = useState(false);

  // Editable fields
  const [fullName, setFullName] = useState("");
  const [phone, setPhone] = useState("");
  const [city, setCity] = useState("");
  const [bio, setBio] = useState("");
  const [hourlyRate, setHourlyRate] = useState("");
  const [experience, setExperience] = useState("");
  const [specializations, setSpecializations] = useState<string[]>([]);
  const [available, setAvailable] = useState(true);

  useEffect(() => { fetchProfile(); }, []);

  const fetchProfile = async () => {
    try {
      const res = await api.get("/profiles/me");
      const p = res.data;
      setProfile(p);
      setFullName(p.full_name || "");
      setPhone(p.phone || "");
      setCity(p.city || "");

      if (p.mechanic_profile) {
        const mp = p.mechanic_profile;
        setMechanicProfile(mp);
        setBio(mp.bio || "");
        setHourlyRate(mp.hourly_rate?.toString() || "");
        setExperience(mp.years_experience?.toString() || "");
        setSpecializations(mp.specializations || []);
        setAvailable(mp.is_available !== false);
      }
    } catch (err: any) {
      setError("Failed to load profile");
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    setSaving(true);
    setError("");
    setSuccess("");
    try {
      await api.patch("/profiles/me", {
        full_name: fullName,
        phone: phone || null,
        city: city || null,
      });

      if (user?.role === "mechanic") {
        await api.patch("/profiles/me/mechanic", {
          bio: bio || null,
          hourly_rate: hourlyRate ? parseFloat(hourlyRate) : null,
          years_experience: experience ? parseInt(experience) : null,
          specializations,
          is_available: available,
        });
      }

      setSuccess("Profile updated successfully!");
      setEditing(false);
      fetchProfile();
    } catch (err: any) {
      setError(err.response?.data?.detail || "Failed to update profile");
    } finally {
      setSaving(false);
    }
  };

  const toggleSpec = (spec: string) => {
    setSpecializations((prev) =>
      prev.includes(spec) ? prev.filter((s) => s !== spec) : [...prev, spec]
    );
  };

  if (loading) return <Box display="flex" justifyContent="center" py={6}><CircularProgress /></Box>;

  return (
    <Box maxWidth={700} mx="auto">
      <Stack direction="row" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h5" fontWeight={700}>My Profile</Typography>
        {!editing ? (
          <Button startIcon={<Edit />} onClick={() => setEditing(true)}>Edit</Button>
        ) : (
          <Stack direction="row" spacing={1}>
            <Button onClick={() => { setEditing(false); fetchProfile(); }}>Cancel</Button>
            <Button variant="contained" startIcon={<Save />}
              onClick={handleSave} disabled={saving}>
              {saving ? "Saving…" : "Save"}
            </Button>
          </Stack>
        )}
      </Stack>

      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}
      {success && <Alert severity="success" sx={{ mb: 2 }}>{success}</Alert>}

      {/* Basic Info */}
      <Card sx={{ mb: 3 }}>
        <CardContent sx={{ p: 3 }}>
          <Stack direction="row" spacing={3} alignItems="center" mb={3}>
            <Avatar sx={{ width: 72, height: 72, bgcolor: "primary.main", fontSize: 28 }}>
              {fullName?.[0] || "U"}
            </Avatar>
            <Box>
              {editing ? (
                <TextField fullWidth label="Full Name" value={fullName}
                  onChange={(e) => setFullName(e.target.value)} size="small" />
              ) : (
                <Typography variant="h6" fontWeight={600}>{fullName || "—"}</Typography>
              )}
              <Chip label={user?.role === "mechanic" ? "Mechanic" : "Car Owner"}
                size="small" color="primary" sx={{ mt: 0.5 }} />
            </Box>
          </Stack>

          <Grid container spacing={2}>
            <Grid size={{ xs: 12, sm: 6 }}>
              <Typography variant="caption" color="text.secondary">Email</Typography>
              <Typography>{user?.email}</Typography>
            </Grid>
            <Grid size={{ xs: 12, sm: 6 }}>
              {editing ? (
                <TextField fullWidth label="Phone" value={phone}
                  onChange={(e) => setPhone(e.target.value)} size="small" />
              ) : (
                <>
                  <Typography variant="caption" color="text.secondary">Phone</Typography>
                  <Typography>{phone || "—"}</Typography>
                </>
              )}
            </Grid>
            <Grid size={{ xs: 12, sm: 6 }}>
              {editing ? (
                <TextField fullWidth label="City" value={city}
                  onChange={(e) => setCity(e.target.value)} size="small" />
              ) : (
                <>
                  <Typography variant="caption" color="text.secondary">City</Typography>
                  <Stack direction="row" spacing={0.5} alignItems="center">
                    <LocationOn fontSize="small" color="action" />
                    <Typography>{city || "—"}</Typography>
                  </Stack>
                </>
              )}
            </Grid>
            <Grid size={{ xs: 12, sm: 6 }}>
              <Typography variant="caption" color="text.secondary">Member Since</Typography>
              <Typography>
                {profile?.created_at ? new Date(profile.created_at).toLocaleDateString() : "—"}
              </Typography>
            </Grid>
          </Grid>
        </CardContent>
      </Card>

      {/* Mechanic-specific */}
      {user?.role === "mechanic" && (
        <Card sx={{ mb: 3 }}>
          <CardContent sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>Mechanic Details</Typography>

            {editing && (
              <FormControlLabel
                control={<Switch checked={available} onChange={(e) => setAvailable(e.target.checked)} />}
                label="Available for new issues" sx={{ mb: 2 }}
              />
            )}

            {!editing && mechanicProfile?.average_rating != null && (
              <Stack direction="row" spacing={1} alignItems="center" mb={2}>
                <Rating value={mechanicProfile.average_rating} readOnly precision={0.5} />
                <Typography variant="body2" color="text.secondary">
                  ({mechanicProfile.total_reviews} reviews)
                </Typography>
              </Stack>
            )}

            <Grid container spacing={2}>
              <Grid size={{ xs: 12 }}>
                {editing ? (
                  <TextField fullWidth multiline rows={3} label="Bio / About"
                    value={bio} onChange={(e) => setBio(e.target.value)}
                    placeholder="Tell car owners about your experience and expertise…" />
                ) : (
                  <>
                    <Typography variant="caption" color="text.secondary">Bio</Typography>
                    <Typography>{bio || "—"}</Typography>
                  </>
                )}
              </Grid>
              <Grid size={{ xs: 6 }}>
                {editing ? (
                  <TextField fullWidth label="Hourly Rate (AED)" type="number"
                    value={hourlyRate} onChange={(e) => setHourlyRate(e.target.value)} />
                ) : (
                  <>
                    <Typography variant="caption" color="text.secondary">Hourly Rate</Typography>
                    <Typography>{hourlyRate ? `AED ${hourlyRate}` : "—"}</Typography>
                  </>
                )}
              </Grid>
              <Grid size={{ xs: 6 }}>
                {editing ? (
                  <TextField fullWidth label="Years of Experience" type="number"
                    value={experience} onChange={(e) => setExperience(e.target.value)} />
                ) : (
                  <>
                    <Typography variant="caption" color="text.secondary">Experience</Typography>
                    <Typography>{experience ? `${experience} years` : "—"}</Typography>
                  </>
                )}
              </Grid>
            </Grid>

            <Divider sx={{ my: 2 }} />

            <Typography variant="subtitle2" gutterBottom>Specializations</Typography>
            <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
              {SPECIALIZATIONS.map((spec) => (
                <Chip key={spec}
                  label={spec.replace(/_/g, " ")}
                  variant={specializations.includes(spec) ? "filled" : "outlined"}
                  color={specializations.includes(spec) ? "primary" : "default"}
                  onClick={editing ? () => toggleSpec(spec) : undefined}
                  sx={{ textTransform: "capitalize" }} />
              ))}
            </Stack>
          </CardContent>
        </Card>
      )}

      {/* Stats Card */}
      <Card>
        <CardContent sx={{ p: 3 }}>
          <Typography variant="h6" gutterBottom>Stats</Typography>
          <Grid container spacing={2}>
            <Grid size={{ xs: 6, sm: 3 }}>
              <Typography variant="caption" color="text.secondary">Issues</Typography>
              <Typography variant="h5" fontWeight={700}>{profile?.total_issues || 0}</Typography>
            </Grid>
            <Grid size={{ xs: 6, sm: 3 }}>
              <Typography variant="caption" color="text.secondary">Conversations</Typography>
              <Typography variant="h5" fontWeight={700}>{profile?.total_conversations || 0}</Typography>
            </Grid>
            {user?.role === "mechanic" && (
              <>
                <Grid size={{ xs: 6, sm: 3 }}>
                  <Typography variant="caption" color="text.secondary">Responses</Typography>
                  <Typography variant="h5" fontWeight={700}>
                    {mechanicProfile?.total_diagnoses || 0}
                  </Typography>
                </Grid>
                <Grid size={{ xs: 6, sm: 3 }}>
                  <Typography variant="caption" color="text.secondary">Rating</Typography>
                  <Typography variant="h5" fontWeight={700}>
                    {mechanicProfile?.average_rating?.toFixed(1) || "—"}
                  </Typography>
                </Grid>
              </>
            )}
          </Grid>
        </CardContent>
      </Card>
    </Box>
  );
}
