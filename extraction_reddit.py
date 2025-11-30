import praw
import pandas as pd
import argparse
import os
 # import inutilisé supprimé

# Configuration Reddit (Récupérée depuis votre ancien script)
CLIENT_ID = os.getenv("REDDIT_CLIENT_ID", "your_client_id")
CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET", "your_client_secret")
USER_AGENT = os.getenv("REDDIT_USER_AGENT", "RedditSentimentAnalytics/1.0")


def extract_reddit_data(subreddits, limit=100, comments_limit=5):
    try:
        reddit = praw.Reddit(
            client_id=CLIENT_ID, client_secret=CLIENT_SECRET, user_agent=USER_AGENT
        )

        all_posts = []
        all_comments = []

        for sub_name in subreddits:
            print(f"Extraction depuis r/{sub_name}...")
            try:
                subreddit = reddit.subreddit(sub_name)

                for post in subreddit.new(limit=limit):
                    # Extraction du Post
                    all_posts.append(
                        {
                            "id": post.id,
                            "title": post.title,
                            "body": post.selftext,
                            "score": post.score,
                            "author": str(post.author),
                            "created_utc": post.created_utc,
                            "subreddit": sub_name,
                            "url": post.url,
                            "num_comments": post.num_comments,
                        }
                    )

                    # Extraction des Commentaires
                    try:
                        post.comments.replace_more(
                            limit=0
                        )  # On ne charge pas les "load more comments" pour aller vite
                        for comment in post.comments.list()[:comments_limit]:
                            all_comments.append(
                                {
                                    "id": comment.id,
                                    "post_id": post.id,
                                    "body": comment.body,
                                    "author": str(comment.author),
                                    "score": comment.score,
                                    "created_utc": comment.created_utc,
                                    "subreddit": sub_name,
                                }
                            )
                    except Exception as e:
                        print(f"Erreur extraction commentaires post {post.id}: {e}")

            except Exception as e:
                print(f"Erreur sur r/{sub_name}: {e}")

        return pd.DataFrame(all_posts), pd.DataFrame(all_comments)

    except Exception as e:
        print(f"Erreur API Reddit : {e}")
        return None, None


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--subreddits", nargs="+", default=["datascience"])
    parser.add_argument("--limit", type=int, default=50)
    parser.add_argument("--comments_limit", type=int, default=5)  # Nouveau paramètre
    args = parser.parse_args()

    print("--- Démarrage de l'extraction ---")
    df_posts, df_comments = extract_reddit_data(
        args.subreddits, args.limit, args.comments_limit
    )

    if df_posts is not None and not df_posts.empty:
        df_posts.to_csv("posts.csv", index=False)
        print(f"Posts sauvegardés dans posts.csv ({len(df_posts)} lignes)")
    else:
        print("Aucun post extrait.")

    if df_comments is not None and not df_comments.empty:
        df_comments.to_csv("comments.csv", index=False)
        print(f"Commentaires sauvegardés dans comments.csv ({len(df_comments)} lignes)")
    else:
        print("Aucun commentaire extrait.")
