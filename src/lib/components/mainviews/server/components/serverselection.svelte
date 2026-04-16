<script lang="ts">
	import * as DropdownMenu from '$lib/components/ui/dropdown-menu';
	import * as Sidebar from '$lib/components/ui/sidebar';
	import { useSidebar } from '$lib/components/ui/sidebar';
	import { onMount } from 'svelte';
	import PlusIcon from '@lucide/svelte/icons/plus';

	type ServerListItem = {
		uuid: string;
		name: string;
	};

	let {
		newServer = () => {}
	}: {
		newServer?: () => void;
	} = $props();

	const sidebar = useSidebar();
	const clamp = (value: number, min = 0, max = 1) => Math.min(Math.max(value, min), max);
	const lerp = (from: number, to: number, progress: number) => from + (to - from) * progress;

	function getTitleFallback(name: string): string {
		const compact = name.replace(/\s+/g, '').toUpperCase();
		if (!compact) {
			return 'NS';
		}

		return compact.slice(0, 2);
	}

	function parseServers(data: unknown): ServerListItem[] {
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

	async function getServers(): Promise<ServerListItem[]> {
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
			return parseServers(data);
		} catch (error) {
			console.error('Failed to load servers:', error);
			return [];
		}
	}

	let collapseProgress = $derived(clamp(sidebar.progress));
	let triggerShellStyle = $derived(
		`width: calc(${(1 - collapseProgress).toFixed(4)} * 100% + ${collapseProgress.toFixed(4)} * 2rem) !important; height: ${lerp(3, 2, collapseProgress).toFixed(4)}rem !important; gap: ${lerp(0.5, 0, collapseProgress).toFixed(4)}rem; padding: ${lerp(0.5, 0, collapseProgress).toFixed(4)}rem ${lerp(0.625, 0, collapseProgress).toFixed(4)}rem !important; will-change: width, height, gap, padding;`
	);

	let servers = $state<ServerListItem[]>([]);
	let selectedServerUuid = $state<string | null>(null);
	let activeServerName = $derived(
		servers.find((server) => server.uuid === selectedServerUuid)?.name ??
			servers[0]?.name ??
			'No servers'
	);

	async function loadServers() {
		servers = await getServers();
		selectedServerUuid = servers[0]?.uuid ?? null;
	}

	onMount(() => {
		void loadServers();
	});
</script>

{#if servers.length === 0}
	<Sidebar.MenuButton
		size="lg"
		style={triggerShellStyle}
		class={`data-[state=open]:bg-sidebar-accent data-[state=open]:text-sidebar-accent-foreground ${collapseProgress > 0.92 ? 'hover:bg-transparent data-[state=open]:bg-transparent' : ''}`}
	>
		<div
			class="flex aspect-square size-8 shrink-0 items-center justify-center rounded-lg bg-sidebar-primary text-sidebar-primary-foreground"
		>
			<span class="text-xs leading-none font-bold">NS</span>
		</div>
		<span class="truncate font-medium">No servers</span>
	</Sidebar.MenuButton>
{:else}
	<Sidebar.Menu>
		<Sidebar.MenuItem>
			<DropdownMenu.Root>
				<DropdownMenu.Trigger>
					<Sidebar.MenuButton
						size="lg"
						style={triggerShellStyle}
						class={`data-[state=open]:bg-sidebar-accent data-[state=open]:text-sidebar-accent-foreground ${collapseProgress > 0.92 ? 'hover:bg-transparent data-[state=open]:bg-transparent' : ''}`}
					>
						<div
							class="flex aspect-square size-8 shrink-0 items-center justify-center rounded-lg bg-sidebar-primary text-sidebar-primary-foreground"
						>
							<span class="text-xs leading-none font-bold">{getTitleFallback(activeServerName)}</span>
						</div>
						<span class="truncate font-medium">{activeServerName}</span>
					</Sidebar.MenuButton>
				</DropdownMenu.Trigger>
				<DropdownMenu.Content
					class="w-(--bits-dropdown-menu-anchor-width) min-w-56 rounded-lg"
					align="start"
					side={sidebar.isMobile ? 'bottom' : 'right'}
					sideOffset={4}
				>
					<DropdownMenu.Label class="text-xs text-muted-foreground">Servers</DropdownMenu.Label>
					{#each servers as server (server.uuid)}
						<DropdownMenu.Item
							onSelect={() => (selectedServerUuid = server.uuid)}
							class="flex w-full items-center gap-2 p-2"
						>
							<div class="flex size-6 items-center justify-center rounded-md border">
								<span class="text-[10px] leading-none font-bold text-foreground">
									{getTitleFallback(server.name)}
								</span>
							</div>
							<span class="truncate">{server.name}</span>
						</DropdownMenu.Item>
					{/each}
					<DropdownMenu.Separator />
					<DropdownMenu.Item
						onSelect={newServer}
						class="flex w-full items-center gap-2 p-2 font-medium text-muted-foreground"
					>
						<div class="flex size-6 items-center justify-center rounded-md border bg-transparent">
							<PlusIcon class="size-4" />
						</div>
						<span>New server</span>
					</DropdownMenu.Item>
				</DropdownMenu.Content>
			</DropdownMenu.Root>
		</Sidebar.MenuItem>
	</Sidebar.Menu>
{/if}
