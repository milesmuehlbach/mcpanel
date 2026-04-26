type ServerListItem = {
	uuid: string;
	name: string;
};

type ActiveServerRuntime = {
	running: boolean;
	status: string;
	prettySoftware: string;
	prettyVersion: string;
};

class ServerState {
	servers = $state.raw<ServerListItem[]>([]);
	selectedServerUuid = $state<string | null>(null);
	isLoading = $state(false);
	loadedOnce = $state(false);

	activeRuntime = $state<ActiveServerRuntime>({
		running: false,
		status: 'stopped',
		prettySoftware: '',
		prettyVersion: ''
	});

	private runtimePollInterval: ReturnType<typeof setInterval> | null = null;
	private runtimePollingConsumers = 0;
	private detailsLoadedForUuid: string | null = null;

	get activeServerRunning(): boolean {
		return this.activeRuntime.running;
	}

	get activeServerStatus(): string {
		return this.activeRuntime.status;
	}

	get activeServerPrettySoftware(): string {
		return this.activeRuntime.prettySoftware;
	}

	get activeServerPrettyVersion(): string {
		return this.activeRuntime.prettyVersion;
	}

	get selectedServer(): ServerListItem | null {
		return this.servers.find((server) => server.uuid === this.selectedServerUuid) ?? null;
	}

	setSelectedServerUuid(uuid: string | null): void {
		if (this.selectedServerUuid === uuid) {
			return;
		}

		this.selectedServerUuid = uuid;
		void this.refreshActiveServerState({ includeDetails: true, forceDetails: true });
	}

	async loadServers(force = false): Promise<void> {
		if (this.isLoading || (this.loadedOnce && !force)) {
			return;
		}

		const previousSelection = this.selectedServerUuid;
		this.isLoading = true;
		const nextServers = await this.fetchServers();
		const hasCurrentSelection = nextServers.some(
			(server) => server.uuid === this.selectedServerUuid
		);

		this.servers = nextServers;
		this.selectedServerUuid = hasCurrentSelection
			? this.selectedServerUuid
			: (nextServers[0]?.uuid ?? null);
		this.loadedOnce = true;
		this.isLoading = false;

		if (previousSelection !== this.selectedServerUuid) {
			void this.refreshActiveServerState({ includeDetails: true, forceDetails: true });
		}
	}

	setActiveServerStatus(status: string, running = this.activeRuntime.running): void {
		this.activeRuntime.status = status;
		this.activeRuntime.running = running;
	}

	attachActiveServerPolling(): () => void {
		this.runtimePollingConsumers += 1;

		if (this.runtimePollInterval === null) {
			void this.refreshActiveServerState({ includeDetails: true });
			this.runtimePollInterval = setInterval(() => {
				void this.refreshActiveServerState({ includeDetails: false });
			}, 1000);
		}

		return () => {
			this.runtimePollingConsumers = Math.max(0, this.runtimePollingConsumers - 1);
			if (this.runtimePollingConsumers === 0 && this.runtimePollInterval !== null) {
				clearInterval(this.runtimePollInterval);
				this.runtimePollInterval = null;
			}
		};
	}

	async refreshActiveServerState({
		includeDetails = true,
		forceDetails = false
	}: {
		includeDetails?: boolean;
		forceDetails?: boolean;
	} = {}): Promise<void> {
		const selectedServer = this.selectedServer;
		if (!selectedServer) {
			this.resetActiveRuntime();
			return;
		}

		const token = sessionStorage.getItem('token');
		if (!token) {
			this.resetActiveRuntime();
			return;
		}

		const statusTask = this.fetchActiveServerStatus(selectedServer.uuid, token);
		const detailsTask = includeDetails
			? this.fetchActiveServerDetails(selectedServer.uuid, token, forceDetails)
			: Promise.resolve();

		await Promise.all([statusTask, detailsTask]);
	}

	private resetActiveRuntime(): void {
		this.activeRuntime.running = false;
		this.activeRuntime.status = 'stopped';
		this.activeRuntime.prettySoftware = '';
		this.activeRuntime.prettyVersion = '';
		this.detailsLoadedForUuid = null;
	}

	private async fetchActiveServerStatus(uuid: string, token: string): Promise<void> {
		try {
			const response = await fetch(`/api/v1/instances/${uuid}/status`, {
				method: 'GET',
				headers: {
					Authorization: `Bearer ${token}`
				}
			});

			if (!response.ok) {
				console.error('Failed to reload server state:', response.statusText);
				return;
			}

			const data = (await response.json()) as { running?: unknown; status?: unknown };
			this.activeRuntime.running = Boolean(data.running);
			this.activeRuntime.status =
				typeof data.status === 'string' && data.status.trim() ? data.status : 'stopped';
		} catch (error) {
			console.error('Error reloading server state:', error);
		}
	}

	private async fetchActiveServerDetails(
		uuid: string,
		token: string,
		force: boolean
	): Promise<void> {
		if (!force && this.detailsLoadedForUuid === uuid) {
			return;
		}

		try {
			const instanceResponse = await fetch(`/api/v1/instances/${uuid}/details`, {
				headers: {
					Authorization: `Bearer ${token}`
				}
			});

			if (!instanceResponse.ok) {
				console.error('Failed to load instance details:', instanceResponse.statusText);
				this.activeRuntime.prettySoftware = '';
				this.activeRuntime.prettyVersion = '';
				this.detailsLoadedForUuid = null;
				return;
			}

			const instanceData = (await instanceResponse.json()) as {
				instance?: { components?: { server_uid?: unknown } };
			};

			const serverUid = instanceData.instance?.components?.server_uid;
			if (typeof serverUid !== 'string' || !serverUid.trim()) {
				this.activeRuntime.prettySoftware = '';
				this.activeRuntime.prettyVersion = '';
				this.detailsLoadedForUuid = null;
				return;
			}

			const componentResponse = await fetch(`/api/v1/components/details?uid=${serverUid}`, {
				headers: {
					Authorization: `Bearer ${token}`
				}
			});

			if (!componentResponse.ok) {
				console.error('Failed to load component details:', componentResponse.statusText);
				this.activeRuntime.prettySoftware = '';
				this.activeRuntime.prettyVersion = '';
				this.detailsLoadedForUuid = null;
				return;
			}

			const componentData = (await componentResponse.json()) as {
				component?: { display_component?: unknown; display_version?: unknown };
			};

			const displayComponent = componentData.component?.display_component;
			const displayVersion = componentData.component?.display_version;

			if (typeof displayComponent === 'string' && displayComponent.trim()) {
				this.activeRuntime.prettySoftware =
					displayComponent === 'Mojang' ? 'Vanilla' : displayComponent;
			} else {
				this.activeRuntime.prettySoftware = '';
			}

			if (typeof displayVersion === 'string' && displayVersion.trim()) {
				this.activeRuntime.prettyVersion = displayVersion;
			} else {
				this.activeRuntime.prettyVersion = '';
			}

			this.detailsLoadedForUuid = uuid;
		} catch (error) {
			console.error('Failed to load active server details:', error);
			this.activeRuntime.prettySoftware = '';
			this.activeRuntime.prettyVersion = '';
			this.detailsLoadedForUuid = null;
		}
	}

	private parseServers(data: unknown): ServerListItem[] {
		const rawInstances = Array.isArray(data)
			? data
			: data &&
				  typeof data === 'object' &&
				  Array.isArray((data as { instances?: unknown }).instances)
				? (data as { instances: unknown[] }).instances
				: [];

		return rawInstances
			.map((instance, index) => {
				if (!instance || typeof instance !== 'object') {
					return null;
				}

				const name = (instance as { name?: unknown }).name;
				if (typeof name !== 'string' || !name.trim()) {
					return null;
				}

				const uuid = (instance as { uuid?: unknown }).uuid;
				return {
					uuid: typeof uuid === 'string' && uuid.trim() ? uuid : `${index}-${name}`,
					name
				};
			})
			.filter((instance): instance is ServerListItem => instance !== null);
	}

	private async fetchServers(): Promise<ServerListItem[]> {
		const token = sessionStorage.getItem('token');
		if (!token) {
			return [];
		}

		try {
			const response = await fetch('/api/v1/instances/list', {
				headers: {
					Authorization: `Bearer ${token}`
				}
			});

			if (!response.ok) {
				return [];
			}

			const data = (await response.json()) as unknown;
			return this.parseServers(data);
		} catch (error) {
			console.error('Failed to load servers:', error);
			return [];
		}
	}
}

export { type ServerListItem };
export const serverState = new ServerState();
