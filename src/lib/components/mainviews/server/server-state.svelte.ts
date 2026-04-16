type ServerListItem = {
	uuid: string;
	name: string;
};

class ServerState {
	servers = $state.raw<ServerListItem[]>([]);
	selectedServerUuid = $state<string | null>(null);
	isLoading = $state(false);
	loadedOnce = $state(false);

	get selectedServer(): ServerListItem | null {
		return this.servers.find((server) => server.uuid === this.selectedServerUuid) ?? null;
	}

	setSelectedServerUuid(uuid: string | null): void {
		this.selectedServerUuid = uuid;
	}

	async loadServers(force = false): Promise<void> {
		if (this.isLoading || (this.loadedOnce && !force)) {
			return;
		}

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
