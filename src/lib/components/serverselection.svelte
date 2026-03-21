<script lang="ts">
	import * as DropdownMenu from '$lib/components/ui/dropdown-menu/index.js';
	import * as Sidebar from '$lib/components/ui/sidebar/index.js';
	import CheckIcon from '@lucide/svelte/icons/check';
	import ChevronsUpDownIcon from '@lucide/svelte/icons/chevrons-up-down';
	import GalleryVerticalEndIcon from '@lucide/svelte/icons/gallery-vertical-end';
	let { servertitles, iconpath }: { servertitles: string[]; iconpath: string[] } = $props();
	let currenttitle = $state(servertitles[0] ?? '');
	let currenticon = $state(iconpath[0] ?? 'none');
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
							{#if currenticon && currenticon !== 'none'}
								<img src={currenticon} alt="Server Icon" class="h-5 w-5 rounded-sm object-cover" />
							{:else}
								<GalleryVerticalEndIcon class="h-5 w-5" />
							{/if}
						</div>
						<div class="flex flex-col gap-0.5 leading-none">
							<span class="font-semibold">{currenttitle}</span>
						</div>
						<ChevronsUpDownIcon class="ms-auto" />
					</Sidebar.MenuButton>
				{/snippet}
			</DropdownMenu.Trigger>
			<DropdownMenu.Content class="w-(--bits-dropdown-menu-anchor-width)" align="start">
				{#each servertitles as version (version)}
					<DropdownMenu.Item onSelect={() => (currenttitle = version)}>
						v{version}
						{#if version === currenttitle}
							<CheckIcon class="ms-auto" />
						{/if}
					</DropdownMenu.Item>
				{/each}
			</DropdownMenu.Content>
		</DropdownMenu.Root>
	</Sidebar.MenuItem>
</Sidebar.Menu>
