<script lang="ts">
	import * as DropdownMenu from '$lib/components/ui/dropdown-menu';
	import * as Sidebar from '$lib/components/ui/sidebar';
	import { useSidebar } from '$lib/components/ui/sidebar';
	import ChevronsUpDownIcon from '@lucide/svelte/icons/chevrons-up-down';
	import PlusIcon from '@lucide/svelte/icons/plus';

	let {
		servertitles = [],
		iconpath = []
	}: {
		servertitles: string[];
		iconpath: string[];
	} = $props();

	const sidebar = useSidebar();

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
</script>

<Sidebar.Menu>
	<Sidebar.MenuItem>
		<DropdownMenu.Root>
			<DropdownMenu.Trigger>
				{#snippet child({ props })}
					<Sidebar.MenuButton
						{...props}
						size="lg"
						class="data-[state=open]:bg-sidebar-accent data-[state=open]:text-sidebar-accent-foreground"
					>
						<div
							class="flex aspect-square size-8 items-center justify-center rounded-lg bg-sidebar-primary text-sidebar-primary-foreground"
						>
							{#if activeIcon}
								<img src={activeIcon} alt={activeTitle} class="size-4" />
							{:else}
								<span class="text-xs leading-none font-bold">{activeTitleFallback}</span>
							{/if}
						</div>
						<div class="grid flex-1 text-start text-sm leading-tight">
							<span class="truncate font-medium">
								{activeTitle}
							</span>
							<span class="truncate text-xs">Minecraft Server</span>
						</div>
						<ChevronsUpDownIcon class="ms-auto" />
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
				<DropdownMenu.Item class="gap-2 p-2">
					<div class="flex size-6 items-center justify-center rounded-md border bg-transparent">
						<PlusIcon class="size-4" />
					</div>
					<div class="font-medium text-muted-foreground">Add server</div>
				</DropdownMenu.Item>
			</DropdownMenu.Content>
		</DropdownMenu.Root>
	</Sidebar.MenuItem>
</Sidebar.Menu>
