<script lang="ts">
	import ServerView from '$lib/components/mainviews/server/serverview.svelte';
	import LoginView from '$lib/components/mainviews/login.svelte';

	let view = 'login';
</script>

{#if view === 'server'}
<ServerView />
{:else if view === 'login'}
	<div class="flex h-screen w-full items-center justify-center px-4">
		<LoginView />
	</div>
{:else if view === 'servercreation'}
	<h1>Server Creation Placeholder</h1>
	{:else if view === 'onboarding'}
	<h1>Onboarding placeholder</h1>
{/if}