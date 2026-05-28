export type TelegramConnectionState = "connected" | "not_connected" | "incomplete";

export type UserSettingsReadModel = {
  profile: {
    email: string;
    displayName: string | null;
    timezone: string;
  };
  account: {
    status: string;
    planName: string;
    planStatus: string;
  };
  telegram: {
    state: TelegramConnectionState;
    username: string | null;
    chatId: string | null;
    guidance: string;
  };
};
