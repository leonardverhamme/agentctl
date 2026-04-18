import { google } from "googleapis";

import { AppConfig } from "../config";
import type { LocalStore } from "../store";

export class GoogleAuthService {
  constructor(
    private readonly config: AppConfig,
    private readonly store: LocalStore,
  ) {}

  isConfigured(): boolean {
    return Boolean(this.config.googleClientId && this.config.googleClientSecret);
  }

  createOAuthClient() {
    return new google.auth.OAuth2(
      this.config.googleClientId,
      this.config.googleClientSecret,
      this.config.googleRedirectUri,
    );
  }

  getAuthorizationUrl(): string {
    if (!this.isConfigured()) {
      throw new Error("Google OAuth is not configured. Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET.");
    }

    const client = this.createOAuthClient();
    return client.generateAuthUrl({
      access_type: "offline",
      prompt: "consent",
      scope: [
        "https://www.googleapis.com/auth/gmail.modify",
        "https://www.googleapis.com/auth/calendar.readonly",
      ],
    });
  }

  async exchangeCodeForToken(code: string): Promise<string | null> {
    if (!this.isConfigured()) {
      throw new Error("Google OAuth is not configured.");
    }

    const client = this.createOAuthClient();
    const { tokens } = await client.getToken(code);
    client.setCredentials(tokens);

    const gmail = google.gmail({ version: "v1", auth: client });
    const profile = await gmail.users.getProfile({ userId: "me" });
    const email = profile.data.emailAddress ?? null;
    await this.store.setOAuthToken("google", JSON.stringify(tokens), email);
    return email;
  }

  async getAuthorizedClient() {
    if (!this.isConfigured()) {
      throw new Error("Google OAuth is not configured.");
    }

    const tokenRecord = await this.store.getOAuthToken("google");
    if (!tokenRecord) {
      throw new Error("Google OAuth token not found. Visit /auth/google/start to connect Gmail and Calendar.");
    }

    const client = this.createOAuthClient();
    client.setCredentials(JSON.parse(tokenRecord.tokenJson));
    return client;
  }
}
