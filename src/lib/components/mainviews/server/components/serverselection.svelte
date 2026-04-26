<script lang="ts">
	import * as DropdownMenu from '$lib/components/ui/dropdown-menu';
	import * as Sidebar from '$lib/components/ui/sidebar';
	import { useSidebar } from '$lib/components/ui/sidebar';
	import { type ServerSubview } from '$lib/components/mainviews/server/server-subroutes';
	import { serverState } from '$lib/components/mainviews/server/server-state.svelte';
	import { Badge } from '$lib/components/ui/badge';
	import Circle from '@lucide/svelte/icons/circle';
	import { Spinner } from '$lib/components/ui/spinner/index.js';
	import { navigate } from 'svelte5-router';
	import { onMount } from 'svelte';
	import PlusIcon from '@lucide/svelte/icons/plus';

	let {
		newServer = () => {},
		activeSubview = 'dashboard'
	}: {
		newServer?: () => void;
		activeSubview?: ServerSubview;
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

	let collapseProgress = $derived(clamp(sidebar.progress));
	let triggerShellStyle = $derived(
		`width: calc(${(1 - collapseProgress).toFixed(4)} * 100% + ${collapseProgress.toFixed(4)} * 2rem) !important; height: ${lerp(3, 2, collapseProgress).toFixed(4)}rem !important; gap: ${lerp(0.5, 0, collapseProgress).toFixed(4)}rem; padding: ${lerp(0.5, 0, collapseProgress).toFixed(4)}rem ${lerp(0.625, 0, collapseProgress).toFixed(4)}rem !important; will-change: width, height, gap, padding;`
	);

	let servers = $derived(serverState.servers);
	let activeServerName = $derived(
		serverState.selectedServer?.name ?? servers[0]?.name ?? 'No servers'
	);
	let activeServerStatus = $derived(serverState.activeServerStatus);
	let activeServerRunning = $derived(serverState.activeServerRunning);
	let activeServerPrettySoftware = $derived(serverState.activeServerPrettySoftware);
	let activeServerPrettyVersion = $derived(serverState.activeServerPrettyVersion);
	let showTriggerMeta = $derived(collapseProgress < 0.45);
	let showTriggerStatus = $derived(collapseProgress < 0.9);

	function selectServer(uuid: string): void {
		serverState.setSelectedServerUuid(uuid);
		navigate(`/servers/${uuid}/${activeSubview}`);
	}

	onMount(() => {
		void serverState.loadServers();
		void serverState.refreshActiveServerState({ includeDetails: true, forceDetails: true });
		const detachPolling = serverState.attachActiveServerPolling();

		return () => {
			detachPolling();
		};
	});
</script>

{#if servers.length === 0}
	<Sidebar.MenuButton
		size="lg"
		style={triggerShellStyle}
		class={`transition-[background-color,color,box-shadow] duration-200 data-[state=open]:bg-sidebar-accent data-[state=open]:text-sidebar-accent-foreground ${collapseProgress > 0.92 ? 'hover:bg-transparent data-[state=open]:bg-transparent' : ''}`}
	>
		<div
			class="flex aspect-square size-8 shrink-0 items-center justify-center rounded-lg bg-sidebar-primary text-sidebar-primary-foreground"
		>
			<span class="text-xs leading-none font-bold">NS</span>
		</div>
		<span class="truncate font-medium">No servers :&lpar;</span>
	</Sidebar.MenuButton>
{:else}
	<Sidebar.Menu>
		<Sidebar.MenuItem>
			<DropdownMenu.Root>
				<DropdownMenu.Trigger class="w-full">
					<Sidebar.MenuButton
						size="lg"
						style={triggerShellStyle}
						class={`transition-[background-color,color,box-shadow] duration-200 data-[state=open]:bg-sidebar-accent data-[state=open]:text-sidebar-accent-foreground ${collapseProgress > 0.92 ? 'hover:bg-transparent data-[state=open]:bg-transparent' : ''}`}
					>
						<div
							class="flex aspect-square size-8 shrink-0 items-center justify-center rounded-lg bg-sidebar-primary text-sidebar-primary-foreground"
						>
							<span class="text-xs leading-none font-bold"
								>{getTitleFallback(activeServerName)}</span
							>
						</div>
						<div class="flex min-w-0 flex-1 flex-col items-start justify-center gap-1 text-left">
							<span class="w-full truncate leading-tight font-medium">{activeServerName}</span>

							{#if showTriggerStatus}
								<div class="flex flex-wrap items-center gap-1.5">
									<Badge
										variant="secondary"
										class="flex items-center gap-1.5 text-[10px] leading-none"
									>
										{#if activeServerStatus === 'running' || activeServerStatus === 'stopped'}
											<Circle
												fill={activeServerRunning ? 'green' : 'red'}
												color={activeServerRunning ? 'green' : 'red'}
												class="size-2"
											/>
										{:else}
											<Spinner class="size-2" />
										{/if}
										{activeServerStatus.charAt(0).toUpperCase() + activeServerStatus.slice(1)}
									</Badge>

									{#if showTriggerMeta}
										{#if activeServerPrettySoftware !== ''}
											<Badge variant="secondary" class="text-[10px] leading-none">
												{activeServerPrettySoftware}
											</Badge>
										{/if}
										{#if activeServerPrettyVersion !== ''}
											<Badge variant="secondary" class="text-[10px] leading-none">
												{activeServerPrettyVersion}
											</Badge>
										{/if}
									{/if}
								</div>
							{/if}
						</div>
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
							onSelect={() => selectServer(server.uuid)}
							class="flex w-full items-center gap-2 p-2 transition-[background-color,color] duration-150 hover:bg-accent hover:text-accent-foreground"
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
						class="flex w-full items-center gap-2 p-2 font-medium text-muted-foreground transition-[background-color,color] duration-150 hover:bg-accent hover:text-accent-foreground"
					>
						<div class="flex size-6 items-center justify-center rounded-md border bg-transparent">
							<PlusIcon class="size-4" />
						</div>
						<span>Create new server</span>
					</DropdownMenu.Item>
				</DropdownMenu.Content>
			</DropdownMenu.Root>
		</Sidebar.MenuItem>
	</Sidebar.Menu>
{/if}
