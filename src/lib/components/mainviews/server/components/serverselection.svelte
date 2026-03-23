<script lang="ts">
	import * as DropdownMenu from '$lib/components/ui/dropdown-menu';
	import * as Sidebar from '$lib/components/ui/sidebar';
	import { useSidebar } from '$lib/components/ui/sidebar';
	import ChevronsUpDownIcon from '@lucide/svelte/icons/chevrons-up-down';
	import PlusIcon from '@lucide/svelte/icons/plus';

	let {
		servertitles = [],
		iconpath = [],
		newServer = () => {}
	}: {
		servertitles: string[];
		iconpath: string[];
		newServer?: () => void;
	} = $props();

	const sidebar = useSidebar();
	const clamp = (value: number, min = 0, max = 1) => Math.min(Math.max(value, min), max);
	const lerp = (from: number, to: number, progress: number) => from + (to - from) * progress;

	let selectedIndex = $state(0);

	const getTitleFallback = (title: string) => {
		const trimmed = title.trim();

		if (!trimmed) return '??';

		const initials = trimmed.slice(0, 2).toUpperCase();
		return initials.length === 1 ? `${initials}?` : initials;
	};

	let activeTitle = $derived(servertitles[selectedIndex] ?? 'No Server');
	let activeIcon = $derived(iconpath[selectedIndex] ?? '');
	let activeTitleFallback = $derived(getTitleFallback(activeTitle));
	let collapseProgress = $derived(clamp(sidebar.progress));
	let triggerShellStyle = $derived(
		`width: calc(${(1 - collapseProgress).toFixed(4)} * 100% + ${collapseProgress.toFixed(4)} * 2rem) !important; height: ${lerp(3, 2, collapseProgress).toFixed(4)}rem !important; gap: ${lerp(0.5, 0, collapseProgress).toFixed(4)}rem; padding: ${lerp(0.5, 0, collapseProgress).toFixed(4)}rem ${lerp(0.625, 0, collapseProgress).toFixed(4)}rem !important; will-change: width, height, gap, padding;`
	);
</script>

<Sidebar.Menu>
	<Sidebar.MenuItem>
		<DropdownMenu.Root>
			<DropdownMenu.Trigger>
				{#snippet child({ props })}
					<Sidebar.MenuButton
						{...props}
						size="lg"
						style={triggerShellStyle}
						class={`data-[state=open]:bg-sidebar-accent data-[state=open]:text-sidebar-accent-foreground ${collapseProgress > 0.92 ? 'hover:bg-transparent data-[state=open]:bg-transparent' : ''}`}
					>
						<div
							class="flex aspect-square size-8 shrink-0 items-center justify-center rounded-lg bg-sidebar-primary text-sidebar-primary-foreground"
						>
							{#if activeIcon}
								<img src={activeIcon} alt={activeTitle} class="size-4" />
							{:else}
								<span class="text-xs leading-none font-bold">{activeTitleFallback}</span>
							{/if}
						</div>
						<div
							data-sidebar="label-stack"
							class="grid min-w-0 flex-1 text-start text-sm leading-tight"
						>
							<span class="truncate font-medium">
								{activeTitle}
							</span>
							<span class="truncate text-xs">Minecraft Server</span>
						</div>
						<span
							data-sidebar="secondary"
							class="ms-auto flex shrink-0 items-center justify-center"
						>
							<ChevronsUpDownIcon class="shrink-0" />
						</span>
					</Sidebar.MenuButton>
				{/snippet}
			</DropdownMenu.Trigger>
			<DropdownMenu.Content
				class="w-(--bits-dropdown-menu-anchor-width) min-w-56 rounded-lg"
				align="start"
				side={sidebar.isMobile ? 'bottom' : 'right'}
				sideOffset={4}
			>
				<DropdownMenu.Label class="text-xs text-muted-foreground">Servers</DropdownMenu.Label>
				{#each servertitles as title, index (title)}
					<DropdownMenu.Item onSelect={() => (selectedIndex = index)} class="gap-2 p-2">
						<div class="flex size-6 items-center justify-center rounded-md border">
							{#if iconpath[index]}
								<img src={iconpath[index]} alt={title} class="size-3.5 shrink-0" />
							{:else}
								<span class="text-[10px] leading-none font-bold text-foreground">
									{getTitleFallback(title)}
								</span>
							{/if}
						</div>
						{title}
					</DropdownMenu.Item>
				{/each}
				<DropdownMenu.Separator />
				<DropdownMenu.Item onSelect={newServer} class="gap-2 p-2">
					<div class="flex size-6 items-center justify-center rounded-md border bg-transparent">
						<PlusIcon class="size-4" />
					</div>
					<div class="font-medium text-muted-foreground">New server</div>
				</DropdownMenu.Item>
			</DropdownMenu.Content>
		</DropdownMenu.Root>
	</Sidebar.MenuItem>
</Sidebar.Menu>
