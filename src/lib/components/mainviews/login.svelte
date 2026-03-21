<script lang="ts">
	import { Button } from '$lib/components/ui/button/index.js';
	import * as Card from '$lib/components/ui/card/index.js';
	import { Input } from '$lib/components/ui/input/index.js';
	import {
		FieldGroup,
		Field,
		FieldLabel,
		FieldDescription
	} from '$lib/components/ui/field/index.js';

	const id = crypto.randomUUID();

	let username = $state('');
	const usernameRegex = /^[A-Za-z0-9_-]+$/;
	let isUsernameValid = $derived(username === '' || usernameRegex.test(username));

	function handleSubmit(e: SubmitEvent) {
		if (!usernameRegex.test(username)) {
			e.preventDefault();
		}
	}
</script>

<Card.Root class="mx-auto w-full max-w-sm">
	<Card.Header>
		<Card.Title class="text-2xl">Login to MCPanel</Card.Title>
	</Card.Header>
	<Card.Content>
		<form onsubmit={handleSubmit}>
			<FieldGroup>
				<Field>
					<FieldLabel for="username-{id}">Username</FieldLabel>
					<Input
						id="username-{id}"
						type="text"
						placeholder="Username"
						required
						bind:value={username}
						pattern="[a-z0-9_-]+"
						oninput={(e) => (username = e.currentTarget.value)}
					/>
					{#if !isUsernameValid}
						<FieldDescription class="text-destructive">
							Username must only contain a-z, 0-9, _ and -
						</FieldDescription>
					{/if}
				</Field>
				<Field>
					<div class="flex items-center">
						<FieldLabel for="password-{id}">Password</FieldLabel>
					</div>
					<Input id="password-{id}" type="password" required placeholder="Password" />
				</Field>
				<Field>
					<Button type="submit" class="w-full" disabled={!isUsernameValid || username === ''}>
						Login
					</Button>
				</Field>
			</FieldGroup>
		</form>
	</Card.Content>
</Card.Root>
