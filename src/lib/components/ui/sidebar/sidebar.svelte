<script lang="ts">
	import * as Sheet from '$lib/components/ui/sheet/index.js';
	import { cn, type WithElementRef } from '$lib/utils.js';
	import type { HTMLAttributes } from 'svelte/elements';
	import { SIDEBAR_WIDTH_ICON_REM, SIDEBAR_WIDTH_MOBILE, SIDEBAR_WIDTH_REM } from './constants.js';
	import { useSidebar } from './context.svelte.js';

	const FLOATING_ICON_GAP_REM = 1;
	const FLOATING_ICON_PANEL_REM = 1.125;

	const clamp = (value: number, min = 0, max = 1) => Math.min(Math.max(value, min), max);
	const lerp = (from: number, to: number, progress: number) => from + (to - from) * progress;
	const joinStyles = (...styles: Array<string | undefined>) => styles.filter(Boolean).join('; ');

	let {
		ref = $bindable(null),
		side = 'left',
		variant = 'sidebar',
		collapsible = 'offcanvas',
		class: className,
		style: styleProp,
		children,
		...restProps
	}: WithElementRef<HTMLAttributes<HTMLDivElement>> & {
		side?: 'left' | 'right';
		variant?: 'sidebar' | 'floating' | 'inset';
		collapsible?: 'offcanvas' | 'icon' | 'none';
	} = $props();

	const sidebar = useSidebar();

	const desktopMotionStyle = $derived.by(() => {
		const progress = clamp(sidebar.progress);
		const inverseProgress = 1 - progress;
		const labelProgress = clamp(progress * 1.35);
		const secondaryProgress = clamp(progress * 1.75);
		const collapsedGapWidthRem =
			variant === 'floating' || variant === 'inset'
				? SIDEBAR_WIDTH_ICON_REM + FLOATING_ICON_GAP_REM
				: SIDEBAR_WIDTH_ICON_REM;
		const collapsedPanelWidthRem =
			variant === 'floating' || variant === 'inset'
				? SIDEBAR_WIDTH_ICON_REM + FLOATING_ICON_PANEL_REM
				: SIDEBAR_WIDTH_ICON_REM;

		let gapWidthRem = SIDEBAR_WIDTH_REM;
		let panelWidthRem = SIDEBAR_WIDTH_REM;
		let translateX = 0;

		if (collapsible === 'icon') {
			gapWidthRem = lerp(SIDEBAR_WIDTH_REM, collapsedGapWidthRem, progress);
			panelWidthRem = lerp(SIDEBAR_WIDTH_REM, collapsedPanelWidthRem, progress);
		} else if (collapsible === 'offcanvas') {
			gapWidthRem = lerp(SIDEBAR_WIDTH_REM, 0, progress);
			translateX = (side === 'left' ? -1 : 1) * progress * 100;
		}

		return joinStyles(
			`--sidebar-progress: ${progress.toFixed(4)}`,
			`--sidebar-progress-inverse: ${inverseProgress.toFixed(4)}`,
			`--sidebar-gap-width: ${gapWidthRem.toFixed(4)}rem`,
			`--sidebar-panel-width: ${panelWidthRem.toFixed(4)}rem`,
			`--sidebar-container-translate: ${translateX.toFixed(4)}%`,
			`--sidebar-button-gap: ${lerp(0.5, 0.125, progress).toFixed(4)}rem`,
			`--sidebar-button-padding: ${lerp(0.625, 0.5, progress).toFixed(4)}rem`,
			`--sidebar-label-width: ${(inverseProgress * 12).toFixed(4)}rem`,
			`--sidebar-label-opacity: ${(1 - labelProgress).toFixed(4)}`,
			`--sidebar-label-shift: ${(-0.65 * labelProgress).toFixed(4)}rem`,
			`--sidebar-label-scale: ${lerp(1, 0.985, labelProgress).toFixed(4)}`,
			`--sidebar-secondary-opacity: ${(1 - secondaryProgress).toFixed(4)}`,
			`--sidebar-secondary-shift: ${(-0.4 * secondaryProgress).toFixed(4)}rem`,
			`--sidebar-submenu-height: ${(inverseProgress * 24).toFixed(4)}rem`,
			styleProp
		);
	});
</script>

{#if collapsible === 'none'}
	<div
		class={cn(
			'flex h-full w-(--sidebar-width) flex-col bg-sidebar text-sidebar-foreground',
			className
		)}
		bind:this={ref}
		style={styleProp}
		{...restProps}
	>
		{@render children?.()}
	</div>
{:else if sidebar.isMobile}
	<Sheet.Root bind:open={() => sidebar.openMobile, (v) => sidebar.setOpenMobile(v)} {...restProps}>
		<Sheet.Content
			bind:ref
			data-sidebar="sidebar"
			data-slot="sidebar"
			data-mobile="true"
			class={cn(
				'w-(--sidebar-width) bg-sidebar p-0 text-sidebar-foreground [&>button]:hidden',
				className
			)}
			style={joinStyles(`--sidebar-width: ${SIDEBAR_WIDTH_MOBILE}`, styleProp)}
			{side}
		>
			<Sheet.Header class="sr-only">
				<Sheet.Title>Sidebar</Sheet.Title>
				<Sheet.Description>Displays the mobile sidebar.</Sheet.Description>
			</Sheet.Header>
			<div class="flex h-full w-full flex-col">
				{@render children?.()}
			</div>
		</Sheet.Content>
	</Sheet.Root>
{:else}
	<div
		bind:this={ref}
		class="group peer hidden text-sidebar-foreground md:block"
		data-state={sidebar.state}
		data-collapsible={sidebar.state === 'collapsed' ? collapsible : ''}
		data-variant={variant}
		data-side={side}
		data-slot="sidebar"
		style={desktopMotionStyle}
	>
		<div
			data-slot="sidebar-gap"
			class={cn(
				'relative shrink-0 bg-transparent',
				(variant === 'floating' || variant === 'inset') && 'pointer-events-none'
			)}
			style="width: var(--sidebar-gap-width); will-change: width;"
		></div>
		<div
			data-slot="sidebar-container"
			class={cn(
				'fixed inset-y-0 z-10 hidden h-svh transform-gpu md:flex',
				side === 'left' ? 'start-0' : 'end-0',
				variant === 'floating' || variant === 'inset'
					? 'p-2'
					: 'group-data-[side=left]:border-e group-data-[side=right]:border-s',
				className
			)}
			style="width: var(--sidebar-panel-width); transform: translate3d(var(--sidebar-container-translate), 0, 0); will-change: width, transform;"
			{...restProps}
		>
			<div
				data-sidebar="sidebar"
				data-slot="sidebar-inner"
				class="flex size-full flex-col overflow-hidden bg-sidebar group-data-[variant=floating]:rounded-lg group-data-[variant=floating]:shadow-sm group-data-[variant=floating]:ring-1 group-data-[variant=floating]:ring-sidebar-border"
			>
				{@render children?.()}
			</div>
		</div>
	</div>
{/if}
