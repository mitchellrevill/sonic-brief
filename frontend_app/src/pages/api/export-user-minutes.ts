import { NextApiRequest, NextApiResponse } from "next";
import { fetchAllUsers, getUserAnalytics } from "@/lib/api";

// /api/export-user-minutes?start=YYYY-MM-DD&end=YYYY-MM-DD
export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  if (req.method !== "GET") {
    return res.status(405).json({ error: "Method not allowed" });
  }
  const { start, end } = req.query;
  if (!start || !end || typeof start !== "string" || typeof end !== "string") {
    return res.status(400).json({ error: "Missing or invalid start/end date" });
  }
  try {
    const users = await fetchAllUsers();
    let csvRows = ["user_email,date,minutes"];
    // Calculate days between start and end
    const startDate = new Date(start);
    const endDate = new Date(end);
    const days = Math.ceil((endDate.getTime() - startDate.getTime()) / (1000 * 60 * 60 * 24)) + 1;
    await Promise.all(
      users.map(async (user) => {
        try {
          const analytics = await getUserAnalytics(user.id, days);
          let dailyMinutes: Record<string, number> | null = null;
          if (analytics.analytics && typeof analytics.analytics === 'object') {
            if ('daily_minutes' in analytics.analytics && typeof (analytics.analytics as any).daily_minutes === 'object') {
              dailyMinutes = (analytics.analytics as any).daily_minutes;
            } else if ('daily_transcription_minutes' in analytics.analytics && typeof (analytics.analytics as any).daily_transcription_minutes === 'object') {
              dailyMinutes = (analytics.analytics as any).daily_transcription_minutes;
            }
          }
          if (dailyMinutes) {
            Object.entries(dailyMinutes).forEach(([date, minutes]) => {
              // Only include dates in range
              if (date >= start && date <= end) {
                csvRows.push(`${user.email},${date},${minutes}`);
              }
            });
          } else if (analytics.analytics?.transcription_stats?.total_minutes !== undefined) {
            csvRows.push(`${user.email},ALL,${analytics.analytics.transcription_stats.total_minutes}`);
          }
        } catch (err) {
          // skip user on error
        }
      })
    );
    const csvContent = csvRows.join("\n");
    res.setHeader("Content-Type", "text/csv");
    res.setHeader("Content-Disposition", `attachment; filename=export_user_minutes_${start}_to_${end}.csv`);
    res.status(200).send(csvContent);
  } catch (err) {
    res.status(500).json({ error: "Failed to export user minutes" });
  }
}
