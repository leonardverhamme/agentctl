import { loadConfig } from "./config";
import { CalendarService } from "./services/calendar";
import { GmailService } from "./services/gmail";
import { GoogleAuthService } from "./services/google-auth";
import { NotionService } from "./services/notion";
import { ReconcileService } from "./services/reconcile";
import { LocalStore } from "./store";

export interface AppContext {
  config: ReturnType<typeof loadConfig>;
  store: LocalStore;
  googleAuth: GoogleAuthService;
  gmail: GmailService;
  calendar: CalendarService;
  notion: NotionService;
  reconcile: ReconcileService;
  close(): void;
}

export function createContext(): AppContext {
  const config = loadConfig();
  const store = new LocalStore(config.sqlitePath);
  const googleAuth = new GoogleAuthService(config, store);
  const gmail = new GmailService(config, store, googleAuth);
  const calendar = new CalendarService(config, store, googleAuth);
  const notion = new NotionService(config);
  const reconcile = new ReconcileService(config, store, gmail, notion);

  return {
    config,
    store,
    googleAuth,
    gmail,
    calendar,
    notion,
    reconcile,
    close() {
      store.close();
    },
  };
}
