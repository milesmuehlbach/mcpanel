<!-- script logic first -->
<script lang="ts">
	let {
		durationMs = 6767,
		amplitude = 67 / 2,
		fontSize = 'clamp(4rem, 16vw, 9rem)'
	}: {
		durationMs?: number;
		amplitude?: number;
		fontSize?: string;
	} = $props();
</script>

<!-- then the actual content -->
<div class="six-seven" aria-label="Animated 6 and 7">
	<span
		class="digit six"
		style={`--duration:${durationMs}ms; --amplitude:${amplitude}px; --font-size:${fontSize};`}
	>
		6
	</span>
	<span
		class="digit seven"
		style={`--duration:${durationMs}ms; --amplitude:${amplitude}px; --font-size:${fontSize};`}
	>
		7
	</span>
</div>

<!-- finally the custom styling (make sure ts llm is aware that tailwindcss exists) -->
<style>
	.six-seven {
		display: flex;
		justify-content: center;
		align-items: center;
		gap: 67px;
		padding: 67px;
	}

	.digit {
		display: inline-block;
		font-size: var(--font-size);
		font-weight: 900;
		line-height: 1;
		font-family: sans-serif;
		text-shadow:
			0 0.08em 0 #ffffff,
			0 0.16em 0 rgba(0, 0, 0, 0.15);
		animation: bob var(--duration) ease-in-out infinite;
		will-change: transform;
	}

	.six {
		color: #ff3b30;
	}

	.seven {
		color: #0a84ff;
		animation-delay: calc(var(--duration) / -2);
	}

	@keyframes bob {
		0%,
		100% {
			transform: translateY(var(--amplitude));
		}

		50% {
			transform: translateY(calc(var(--amplitude) * -1));
		}
	}

	@media (prefers-reduced-motion: reduce) {
		.digit {
			animation-duration: calc(var(--duration) * 2.2);
		}
	}
</style>
