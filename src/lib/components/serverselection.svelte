<script lang="ts">
	import * as DropdownMenu from '$lib/components/ui/dropdown-menu/index.js';
	import * as Sidebar from '$lib/components/ui/sidebar/index.js';
	import CheckIcon from '@lucide/svelte/icons/check';
	import ChevronsUpDownIcon from '@lucide/svelte/icons/chevrons-up-down';
	import GalleryVerticalEndIcon from '@lucide/svelte/icons/gallery-vertical-end';
	let { servertitles = [], iconpath = [] }: { servertitles: string[]; iconpath: string[] } =
		$props();

	let selectedIndex = $state(0);

	let displayTitle = $derived(servertitles[selectedIndex] ?? 'No Server Selected');
	let displayIcon = $derived(iconpath[selectedIndex] ?? 'none');
</script>

<Sidebar.Menu>
	<Sidebar.MenuItem>
		<DropdownMenu.Root>
			<DropdownMenu.Trigger>
				{#snippet child({ props })}
					<Sidebar.MenuButton
						size="lg"
						class="data-[state=open]:bg-sidebar-accent data-[state=open]:text-sidebar-accent-foreground"
						{...props}
					>
						<div
							class="flex aspect-square size-8 items-center justify-center rounded-lg bg-sidebar-primary text-sidebar-primary-foreground"
						>
							{#if displayIcon && displayIcon !== 'none'}
								<img src={displayIcon} alt="Server Icon" class="h-5 w-5 rounded-sm object-cover" />
							{:else}
								<GalleryVerticalEndIcon class="h-5 w-5" />
							{/if}
						</div>
						<div class="flex flex-col gap-0.5 leading-none">
							<span class="font-semibold">{displayTitle}</span>
						</div>
						<ChevronsUpDownIcon class="ms-auto" />
					</Sidebar.MenuButton>
				{/snippet}
			</DropdownMenu.Trigger>
			<DropdownMenu.Content class="w-(--bits-dropdown-menu-anchor-width)" align="start">
				{#each servertitles as version, i (version)}
					<DropdownMenu.Item onSelect={() => (selectedIndex = i)}>
						{version}
						{#if i === selectedIndex}
							<CheckIcon class="ms-auto" />
						{/if}
					</DropdownMenu.Item>
				{/each}
			</DropdownMenu.Content>
		</DropdownMenu.Root>
	</Sidebar.MenuItem>
</Sidebar.Menu>
