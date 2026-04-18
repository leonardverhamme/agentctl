import { calendar_v3, google } from "googleapis";

import { AppConfig } from "../config";
import { stableHash } from "../lib/hash";
import { compactText, unique } from "../lib/text";
import { nowIso } from "../lib/time";
import type { LocalStore } from "../store";
import { CalendarEventSnapshot } from "../types";
import { GoogleAuthService } from "./google-auth";

export class CalendarService {
  constructor(
    private readonly config: AppConfig,
    private readonly store: LocalStore,
    private readonly auth: GoogleAuthService,
  ) {}

  async syncCalendar(): Promise<{ mode: "full" | "incremental"; events: CalendarEventSnapshot[]; fallbackUsed: boolean }> {
    const client = await this.auth.getAuthorizedClient();
    const calendar = google.calendar({ version: "v3", auth: client });
    const previousSyncToken = await this.store.getSyncState("calendar", "syncToken");
    let fallbackUsed = false;
    let mode: "full" | "incremental" = previousSyncToken ? "incremental" : "full";
    const events: CalendarEventSnapshot[] = [];

    const requestBase: calendar_v3.Params$Resource$Events$List = {
      calendarId: this.config.googleCalendarId,
      showDeleted: true,
      singleEvents: false,
      maxResults: 250,
    };

    if (previousSyncToken) {
      requestBase.syncToken = previousSyncToken;
    } else {
      requestBase.timeMin = new Date(Date.now() - this.config.googleCalendarLookbackDays * 24 * 60 * 60 * 1000).toISOString();
      requestBase.timeMax = new Date(Date.now() + this.config.googleCalendarLookaheadDays * 24 * 60 * 60 * 1000).toISOString();
    }

    let nextSyncToken = previousSyncToken ?? "";
    let pageToken: string | undefined;

    do {
      try {
        const response = await calendar.events.list({
          ...requestBase,
          pageToken,
        });
        for (const item of response.data.items ?? []) {
          const snapshot = this.toEventSnapshot(item);
          if (!snapshot) {
            continue;
          }
          events.push(snapshot);
          await this.store.upsertSourceCache("calendar", "event", snapshot.eventId, stableHash(snapshot), snapshot);
        }
        nextSyncToken = response.data.nextSyncToken ?? nextSyncToken;
        pageToken = response.data.nextPageToken ?? undefined;
      } catch (error) {
        const httpStatus = (error as { code?: number }).code;
        if (httpStatus !== 410) {
          throw error;
        }
        fallbackUsed = true;
        mode = "full";
        pageToken = undefined;
        requestBase.syncToken = undefined;
        requestBase.timeMin = new Date(Date.now() - this.config.googleCalendarLookbackDays * 24 * 60 * 60 * 1000).toISOString();
        requestBase.timeMax = new Date(Date.now() + this.config.googleCalendarLookaheadDays * 24 * 60 * 60 * 1000).toISOString();
      }
    } while (pageToken);

    if (nextSyncToken) {
      await this.store.setSyncState("calendar", "syncToken", nextSyncToken);
      await this.store.setSyncState("calendar", "lastSyncAt", nowIso());
    }

    return { mode, events, fallbackUsed };
  }

  private toEventSnapshot(event: calendar_v3.Schema$Event): CalendarEventSnapshot | null {
    if (!event.id || !event.start || !event.end) {
      return null;
    }

    const startAt = event.start.dateTime ?? event.start.date;
    const endAt = event.end.dateTime ?? event.end.date;
    if (!startAt || !endAt) {
      return null;
    }

    return {
      eventId: event.id,
      summary: compactText(event.summary ?? "Untitled event", 120),
      description: compactText(event.description ?? "", 300),
      organizerEmail: event.organizer?.email ?? "",
      attendees: unique((event.attendees ?? []).map((attendee) => attendee.email ?? "").filter(Boolean)),
      status: event.status ?? "confirmed",
      startAt: new Date(startAt).toISOString(),
      endAt: new Date(endAt).toISOString(),
      updatedAt: event.updated ?? new Date().toISOString(),
      htmlLink: event.htmlLink ?? "",
    };
  }
}
